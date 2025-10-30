import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from src.compare import (
    CompareResults,
    compare_dataframes,
    create_output_folder,
    get_file_header,
    get_filename_without_extension,
    read_files_in_parallel,
    write_results_in_parallel,
)

# GUI imports - only loaded when needed
GUI_AVAILABLE = True
try:
    import threading
    import tkinter as tk
    import webbrowser
    from tkinter import filedialog, messagebox, ttk

    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    GUI_AVAILABLE = False


@dataclass
class OutputConfig:
    """Configuration for output file generation and GUI display."""

    key: str
    filename_template: str
    button_text_template: str
    order: int


class ResultsManager:
    """Manages result file organization and GUI output generation."""

    OUTPUT_CONFIGS = [
        OutputConfig("missing_in_file1", "Missing_in_{file1_name}.csv", "Open Missing in '{file1_name}'", 1),
        OutputConfig("missing_in_file2", "Missing_in_{file2_name}.csv", "Open Missing in '{file2_name}'", 2),
        OutputConfig("mismatches", "Row_Mismatches_{file1_name}_vs_{file2_name}.csv", "Open Row Mismatches", 3),
        OutputConfig(
            "unpivoted_mismatches",
            "Value_Unpivoted_Mismatches_{file1_name}_vs_{file2_name}.csv",
            "Open Value (unpivoted) Mismatches",
            4,
        ),
        OutputConfig("duplicates_file1", "Duplicates_in_{file1_name}.csv", "Open Duplicates in '{file1_name}'", 5),
        OutputConfig("duplicates_file2", "Duplicates_in_{file2_name}.csv", "Open Duplicates in '{file2_name}'", 6),
    ]

    def __init__(self, file1_name: str, file2_name: str):
        self.file1_name = file1_name
        self.file2_name = file2_name

    def prepare_results_for_writing(self, comparison_results: dict) -> dict:
        """Prepare results dictionary for parallel writing."""
        results_dict = {}
        for config in self.OUTPUT_CONFIGS:
            if config.key in comparison_results:
                filename = config.filename_template.format(file1_name=self.file1_name, file2_name=self.file2_name)
                results_dict[config.key] = (comparison_results[config.key], filename)
        return results_dict

    def get_output_buttons_config(self, saved_files: list[str]) -> list[tuple[str, str]]:
        """Generate ordered list of (filename, button_text) for GUI buttons."""
        saved_files_map = {Path(p).name: p for p in saved_files}
        buttons_config = []

        for config in sorted(self.OUTPUT_CONFIGS, key=lambda x: x.order):
            filename = config.filename_template.format(file1_name=self.file1_name, file2_name=self.file2_name)
            if filename in saved_files_map:
                button_text = config.button_text_template.format(file1_name=self.file1_name, file2_name=self.file2_name)
                buttons_config.append((saved_files_map[filename], button_text))

        return buttons_config


def cli_mode():
    """Command line interface for data comparison."""
    parser = argparse.ArgumentParser(description="DataCompare - A tool to compare CSV and Excel files using Polars.")
    parser.add_argument("file1", help="First data file (CSV or Excel)")
    parser.add_argument("file2", help="Second data file (CSV or Excel)")
    parser.add_argument(
        "--keys", help="Key columns for comparison (comma-separated). Optional if mapping file provided."
    )
    parser.add_argument("--mapping", help="Column mapping file (CSV format)")
    parser.add_argument("--output", help="Output folder base name (optional)")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (disallow nulls in key columns)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary to stdout")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (DEBUG) logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Reduce logging to WARNING")
    args = parser.parse_args()

    # Configure logging with precedence: verbose > quiet > log-level
    level = getattr(logging, args.log_level.upper())
    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    if args.json and level < logging.WARNING:
        level = logging.WARNING
    logging.basicConfig(level=level)

    # Validate arguments
    if not args.keys and not args.mapping:
        parser.error("Either --keys or --mapping must be provided")

    # Parse key columns - split only on commas, preserve spaces in column names
    args.keys = [key.strip() for key in args.keys.split(",") if key.strip()] if args.keys else []

    try:
        start_time = time.perf_counter()

        if not args.json:
            print("Loading files...")
        df1, df2 = read_files_in_parallel(args.file1, args.file2)
        load_time = time.perf_counter() - start_time
        if not args.json:
            print(f"Files loaded in {load_time:.2f} seconds.")

        file1_name = get_filename_without_extension(args.file1)
        file2_name = get_filename_without_extension(args.file2)
        results_manager = ResultsManager(file1_name, file2_name)

        # Perform comparison with optional mapping
        cmp_start = time.perf_counter()
        results: CompareResults = compare_dataframes(
            df1, df2, args.keys, file1_name, file2_name, args.mapping, strict=args.strict
        )
        compare_time = time.perf_counter() - cmp_start

        # Display statistics
        if not args.json:
            print("\n--- Statistics ---")
            print(f"File 1 ({Path(args.file1).name}): {results.df1_shape[0]} rows, {results.df1_shape[1]} columns")
            print(f"File 2 ({Path(args.file2).name}): {results.df2_shape[0]} rows, {results.df2_shape[1]} columns")
            print(f"Rows missing in {file1_name}: {len(results.missing_in_file1)}")
            print(f"Rows missing in {file2_name}: {len(results.missing_in_file2)}")
            print(f"Row Mismatches: {len(results.mismatches)}")
            print(f"Duplicate keys in {file1_name}: {len(results.duplicates_file1)}")
            print(f"Duplicate keys in {file2_name}: {len(results.duplicates_file2)}")
            print(f"Value (unpivoted) Mismatches: {len(results.unpivoted_mismatches)}")
            print("--------------------")

        # Create output folder and save results
        output_folder = create_output_folder()
        if not args.json:
            print(f"\nCreated output folder: {output_folder}")

        write_start = time.perf_counter()
        results_dict = {
            "missing_in_file1": results.missing_in_file1,
            "missing_in_file2": results.missing_in_file2,
            "mismatches": results.mismatches,
            "duplicates_file1": results.duplicates_file1,
            "duplicates_file2": results.duplicates_file2,
            "unpivoted_mismatches": results.unpivoted_mismatches,
        }

        prepared_results = results_manager.prepare_results_for_writing(results_dict)
        saved_files = write_results_in_parallel(prepared_results, output_folder)

        write_time = time.perf_counter() - write_start
        if not args.json:
            print("\nWriting results...")
            print(f"Results written in {write_time:.2f} seconds.")

        # Display saved file paths as URIs for clickable links
        saved_uris = [str(Path(fp).absolute().as_uri()) for fp in saved_files]
        if not args.json:
            print("\nResults saved to:")
            for uri in saved_uris:
                print(f"  - {uri}")

        total_time = time.perf_counter() - start_time
        if not args.json:
            print(f"\nTotal processing time: {total_time:.2f} seconds.")

        # Optional JSON summary
        if args.json:
            file1_info = {
                "path": str(Path(args.file1)),
                "name": Path(args.file1).name,
                "rows": results.df1_shape[0],
                "cols": results.df1_shape[1],
            }
            file2_info = {
                "path": str(Path(args.file2)),
                "name": Path(args.file2).name,
                "rows": results.df2_shape[0],
                "cols": results.df2_shape[1],
            }
            stats = {
                "missing_in_file1": len(results.missing_in_file1),
                "missing_in_file2": len(results.missing_in_file2),
                "row_mismatches": len(results.mismatches),
                "duplicates_file1": len(results.duplicates_file1),
                "duplicates_file2": len(results.duplicates_file2),
                "value_mismatches": len(results.unpivoted_mismatches),
            }
            timing = {
                "load_sec": round(load_time, 3),
                "compare_sec": round(compare_time, 3),
                "write_sec": round(write_time, 3),
                "total_sec": round(total_time, 3),
            }
            summary = {
                "file1": file1_info,
                "file2": file2_info,
                "keys": args.keys,
                "mapping_file": str(Path(args.mapping)) if args.mapping else None,
                "stats": stats,
                "outputs": saved_uris,
                "timing": timing,
            }
            print(json.dumps(summary, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


class DataCompareApp(TkinterDnD.Tk):
    """A class-based GUI for the Data Comparison Tool."""

    def __init__(self):
        super().__init__()
        self.title("DataCompare - Advanced File Comparison Tool")
        self.geometry("800x900")

        # --- Application State ---
        self.file1_var = tk.StringVar()
        self.file2_var = tk.StringVar()
        self.keys_var = tk.StringVar()
        self.mapping_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.comparison_results = {}
        self.results_manager: ResultsManager | None = None

        # --- UI Setup ---
        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        """Configure styles for UI elements."""
        style = ttk.Style(self)
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        style.configure("Header.TLabel", font=("Helvetica", 12, "bold"))

    def _create_widgets(self):
        """Create and layout all the widgets in the main window."""
        # --- Main Frames ---
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill="x")

        middle_frame = ttk.Frame(self, padding=10)
        middle_frame.pack(fill="x", expand=True)

        # --- Input Section ---
        input_frame = ttk.LabelFrame(top_frame, text="1. Inputs", padding=(10, 5))
        input_frame.pack(fill="x", expand=True)
        self._create_input_widgets(input_frame)

        # --- Compare Button ---
        compare_button_frame = ttk.Frame(top_frame, padding=(0, 10))
        compare_button_frame.pack(fill="x")
        self.compare_button = ttk.Button(
            compare_button_frame, text="Compare Files", command=self._run_comparison, style="Accent.TButton"
        )
        self.compare_button.pack(pady=5)

        # --- Dashboard Section ---
        dashboard_frame = ttk.LabelFrame(top_frame, text="2. Comparison Results", padding=(10, 5))
        dashboard_frame.pack(fill="x", expand=True, pady=(0, 10))
        self._create_dashboard_widgets(dashboard_frame)

        # --- Save Button ---
        save_button_frame = ttk.Frame(middle_frame, padding=(0, 10))
        save_button_frame.pack(fill="x")
        self.save_button = ttk.Button(
            save_button_frame, text="Save Results", command=self._save_results, state="disabled"
        )
        self.save_button.pack(pady=5)

        # --- Output Section ---
        self.output_frame = ttk.LabelFrame(middle_frame, text="3. Outputs", padding=(10, 5))
        self.output_frame.pack(fill="x", expand=True)

        # --- Status Bar ---
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill="x", padx=10, pady=5, side="bottom")

    def _create_input_widgets(self, parent_frame):
        """Creates the file and key input widgets."""
        ttk.Label(parent_frame, text="File 1:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        file1_entry = ttk.Entry(parent_frame, textvariable=self.file1_var, width=60)
        file1_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(parent_frame, text="Browse...", command=lambda: self._browse_file(self.file1_var)).grid(
            row=0, column=2, padx=5, pady=2
        )
        self._setup_drag_and_drop(file1_entry, self.file1_var, is_file_entry=True)

        ttk.Label(parent_frame, text="File 2:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        file2_entry = ttk.Entry(parent_frame, textvariable=self.file2_var, width=60)
        file2_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(parent_frame, text="Browse...", command=lambda: self._browse_file(self.file2_var)).grid(
            row=1, column=2, padx=5, pady=2
        )
        self._setup_drag_and_drop(file2_entry, self.file2_var, is_file_entry=True)

        # Add separator
        ttk.Separator(parent_frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(parent_frame, text="Column Mapping:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        mapping_entry = ttk.Entry(parent_frame, textvariable=self.mapping_var, width=60)
        mapping_entry.grid(row=3, column=1, padx=5, pady=2)
        ttk.Button(parent_frame, text="Browse...", command=self._browse_mapping_file).grid(
            row=3, column=2, padx=5, pady=2
        )
        self._setup_drag_and_drop(mapping_entry, self.mapping_var)

        # Help text for mapping
        help_text = ttk.Label(
            parent_frame,
            text="Optional: CSV file with mapping_type,file1_column,file2_column format",
            font=("Helvetica", 8),
            foreground="gray",
        )
        help_text.grid(row=4, column=1, sticky="w", padx=5, pady=(0, 5))

        ttk.Label(parent_frame, text="Key Columns:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        keys_entry = ttk.Entry(parent_frame, textvariable=self.keys_var, width=60)
        keys_entry.grid(row=5, column=1, padx=5, pady=2)
        ttk.Button(parent_frame, text="Suggest", command=self._suggest_key_columns).grid(
            row=5, column=2, padx=5, pady=2
        )
        self._setup_drag_and_drop(keys_entry, self.keys_var)

        # Help text for keys
        help_text2 = ttk.Label(
            parent_frame,
            text="Comma-separated. Optional if mapping file defines key columns",
            font=("Helvetica", 8),
            foreground="gray",
        )
        help_text2.grid(row=6, column=1, sticky="w", padx=5, pady=(0, 5))

    def _create_dashboard_widgets(self, parent_frame):
        """Creates the labels for displaying comparison statistics."""
        self.stat_labels = {}
        self.stat_values = {}

        # Centralized stats configuration for better maintainability
        stats_config = [
            ("file1_stats", "File 1 Stats:"),
            ("file2_stats", "File 2 Stats:"),
            ("missing_in_file1", "Missing in File 1:"),
            ("missing_in_file2", "Missing in File 2:"),
            ("mismatches", "Row Mismatches:"),
            ("unpivoted_mismatches", "Value (unpivoted) Mismatches:"),
            ("duplicates_file1", "Duplicates in File 1:"),
            ("duplicates_file2", "Duplicates in File 2:"),
        ]

        columns = 2
        for col in range(columns * 2):
            parent_frame.grid_columnconfigure(col, weight=1)

        common_keys = {"mismatches", "unpivoted_mismatches"}
        standard_stats = [item for item in stats_config if item[0] not in common_keys]
        centered_stats = [item for item in stats_config if item[0] in common_keys]

        for index, (key, text) in enumerate(standard_stats):
            col_group = index % columns
            row = index // columns
            label_col = col_group * 2
            value_col = label_col + 1

            label = ttk.Label(parent_frame, text=text)
            label.grid(row=row, column=label_col, sticky="w", padx=5, pady=2)
            value_var = tk.StringVar(value="N/A")
            value_label = ttk.Label(parent_frame, textvariable=value_var, font=("Helvetica", 10, "bold"))
            value_label.grid(row=row, column=value_col, sticky="w", padx=5, pady=2)
            self.stat_labels[key] = label
            self.stat_values[key] = value_var

        center_row = (len(standard_stats) + columns - 1) // columns
        for offset, (key, text) in enumerate(centered_stats):
            frame = ttk.Frame(parent_frame)
            frame.grid(row=center_row + offset, column=0, columnspan=columns * 2, pady=(10 if offset == 0 else 2, 2))
            label = ttk.Label(frame, text=text)
            label.pack(side="left", padx=(0, 5))
            value_var = tk.StringVar(value="N/A")
            value_label = ttk.Label(frame, textvariable=value_var, font=("Helvetica", 10, "bold"))
            value_label.pack(side="left")
            self.stat_labels[key] = label
            self.stat_values[key] = value_var

    def _setup_drag_and_drop(self, widget, string_var, is_file_entry=False):
        """Configures a widget to accept file drops."""

        def drop(event):
            path = event.data.strip()
            if path.startswith("{") and path.endswith("}"):
                path = path[1:-1]
            string_var.set(path)
            if is_file_entry:
                self._suggest_key_columns()
            return event.action

        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", drop)

    def _browse_file(self, var):
        """Opens a file dialog and sets the selected path to the given variable."""
        path = filedialog.askopenfilename(
            filetypes=[
                ("All Supported", "*.xlsx;*.xls;*.csv"),
                ("Excel Files", "*.xlsx;*.xls"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*"),
            ]
        )
        if path:
            var.set(path)
            self._suggest_key_columns()

    def _browse_mapping_file(self):
        """Opens a file dialog for selecting a mapping file."""
        path = filedialog.askopenfilename(
            title="Select Column Mapping File", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if path:
            self.mapping_var.set(path)
            self._validate_mapping_file()

    def _validate_mapping_file(self):
        """Validates the selected mapping file and provides feedback."""
        mapping_path = self.mapping_var.get()
        if not mapping_path:
            return

        try:
            from compare import ColumnMapper

            mapper = ColumnMapper(mapping_path)
            self.status_var.set(
                f"Mapping file loaded: {len(mapper.key_mappings)} key, {len(mapper.data_mappings)} data mappings"
            )
        except Exception as e:
            self.status_var.set(f"Mapping file error: {str(e)}")
            messagebox.showerror("Mapping File Error", f"Error loading mapping file:\n{str(e)}")

    def _suggest_key_columns(self):
        """Suggests common columns as keys if both file paths are available."""
        f1 = self.file1_var.get()
        f2 = self.file2_var.get()
        if f1 and f2:
            self.status_var.set("Reading headers to suggest keys...")
            self.update_idletasks()
            try:
                header1 = set(get_file_header(f1))
                header2 = set(get_file_header(f2))
                if header1 and header2:
                    common_keys = sorted(list(header1.intersection(header2)))
                    self.keys_var.set(", ".join(common_keys))
                    self.status_var.set("Suggested common columns as keys. Please verify.")
                else:
                    self.status_var.set("Could not read headers to suggest keys.")
            except Exception as e:
                self.status_var.set(f"Error reading headers: {e}")
        else:
            self.status_var.set("Ready")

    def _clear_previous_results(self):
        """Resets the dashboard and output sections."""
        for key in self.stat_values:
            self.stat_values[key].set("N/A")
        for widget in self.output_frame.winfo_children():
            widget.destroy()
        self.comparison_results.clear()
        self.save_button.config(state="disabled")

    def _run_comparison(self):
        """Starts the file comparison process in a background thread."""
        if not self.file1_var.get() or not self.file2_var.get():
            messagebox.showerror("Error", "Please select both files.")
            return

        # Validate that either keys or mapping is provided
        if not self.keys_var.get() and not self.mapping_var.get():
            messagebox.showerror("Error", "Please provide either key columns or a mapping file.")
            return

        self._clear_previous_results()
        self.compare_button.config(state="disabled")
        thread = threading.Thread(target=self._comparison_worker, daemon=True)
        thread.start()

    def _comparison_worker(self):
        """The actual comparison logic that runs in a separate thread."""
        try:
            self.after(0, lambda: self.status_var.set("Loading files..."))
            df1, df2 = read_files_in_parallel(self.file1_var.get(), self.file2_var.get())

            self.after(0, lambda: self.status_var.set("Comparing files..."))
            key_cols = [k.strip() for k in self.keys_var.get().split(",") if k.strip()] if self.keys_var.get() else []

            file1_name = get_filename_without_extension(self.file1_var.get())
            file2_name = get_filename_without_extension(self.file2_var.get())
            self.results_manager = ResultsManager(file1_name, file2_name)

            mapping_file = self.mapping_var.get() if self.mapping_var.get() else None
            results = compare_dataframes(df1, df2, key_cols, file1_name, file2_name, mapping_file)
            self.after(0, self._update_gui_with_results, results)
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.after(0, lambda: self.status_var.set("Error occurred"))
        finally:
            self.after(0, lambda: self.compare_button.config(state="normal"))

    def _update_gui_with_results(self, results: CompareResults):
        """Updates the GUI with comparison results. Must be called on the main thread."""
        # Note: GUI labels invert missing_X naming for user readability
        self.comparison_results = {
            "missing_in_file1": results.missing_in_file1,
            "missing_in_file2": results.missing_in_file2,
            "mismatches": results.mismatches,
            "duplicates_file1": results.duplicates_file1,
            "duplicates_file2": results.duplicates_file2,
            "unpivoted_mismatches": results.unpivoted_mismatches,
        }

        self.stat_values["file1_stats"].set(f"{results.df1_shape[0]} rows, {results.df1_shape[1]} columns")
        self.stat_values["file2_stats"].set(f"{results.df2_shape[0]} rows, {results.df2_shape[1]} columns")
        self.stat_values["missing_in_file1"].set(f"{len(results.missing_in_file1)} rows")
        self.stat_values["missing_in_file2"].set(f"{len(results.missing_in_file2)} rows")
        self.stat_values["mismatches"].set(f"{len(results.mismatches)} rows")
        self.stat_values["duplicates_file1"].set(f"{len(results.duplicates_file1)} rows")
        self.stat_values["duplicates_file2"].set(f"{len(results.duplicates_file2)} rows")
        self.stat_values["unpivoted_mismatches"].set(f"{len(results.unpivoted_mismatches)} rows")

        f1_name, f2_name = self.results_manager.file1_name, self.results_manager.file2_name
        self.stat_labels["file1_stats"].config(text=f"'{f1_name}' Stats:")
        self.stat_labels["file2_stats"].config(text=f"'{f2_name}' Stats:")
        self.stat_labels["missing_in_file1"].config(text=f"Missing in '{f1_name}':")
        self.stat_labels["missing_in_file2"].config(text=f"Missing in '{f2_name}':")
        self.stat_labels["duplicates_file1"].config(text=f"Duplicates in '{f1_name}':")
        self.stat_labels["duplicates_file2"].config(text=f"Duplicates in '{f2_name}':")

        self.status_var.set("Comparison complete. Ready to save results.")
        self.save_button.config(state="normal")

    def _save_results(self):
        """Saves the comparison results to CSV files."""
        if not self.comparison_results or not self.results_manager:
            messagebox.showerror("Error", "No comparison has been run yet.")
            return
        try:
            self.status_var.set("Saving results...")
            self.update_idletasks()
            output_folder = create_output_folder()

            results_dict = self.results_manager.prepare_results_for_writing(self.comparison_results)
            saved_files = write_results_in_parallel(results_dict, output_folder)

            # Clear existing output widgets
            for widget in self.output_frame.winfo_children():
                widget.destroy()

            if saved_files:
                ttk.Label(self.output_frame, text=f"Results saved to: {Path(output_folder).resolve()}").pack(
                    anchor="w", pady=(0, 5)
                )

                # Create buttons using the streamlined configuration
                buttons_config = self.results_manager.get_output_buttons_config(saved_files)
                for file_path, button_text in buttons_config:
                    btn = ttk.Button(
                        self.output_frame,
                        text=button_text,
                        command=lambda p=file_path: self._open_file_in_system(p),
                    )
                    btn.pack(anchor="w", fill="x", pady=2)

                self.status_var.set("Results saved successfully.")
            else:
                ttk.Label(self.output_frame, text="No differences or duplicates found to save.").pack(anchor="w")
                self.status_var.set("No differences found.")

            self.save_button.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")
            self.status_var.set("Save failed")

    def _open_file_in_system(self, path):
        """Opens a file using the system's default application."""
        try:
            uri = Path(path).resolve().as_uri()
            webbrowser.open(uri)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")


def main():
    # The presence of '--gui' or no arguments will launch the GUI.
    # Any other arguments will trigger the CLI mode.
    if "--gui" in sys.argv or len(sys.argv) == 1:
        if not GUI_AVAILABLE:
            print(
                "GUI dependencies not available. Use CLI mode or install: uv pip install tkinterdnd2", file=sys.stderr
            )
            sys.exit(1)
        app = DataCompareApp()
        app.mainloop()
    else:
        cli_mode()


if __name__ == "__main__":
    main()
