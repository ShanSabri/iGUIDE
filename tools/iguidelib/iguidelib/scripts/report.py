import os
import sys
import argparse
import subprocess

from ruamel.yaml import YAML
from pathlib import Path
from iguidelib.scripts.evaluate import main as Eval

def main( argv = sys.argv ):
    """Generate a custom report from iGUIDE output files."""

    try:
        conda_prefix = os.environ.get("CONDA_PREFIX")
    except (KeyError, IndexError):
        raise SystemExit(
            "Could not determine Conda prefix. Activate your iGUIDE "
            "environment and try this command again.")

    usage_str = (
        "  \n"
        "  iguide %(prog)s -c <path/to/config.file> <options>\n"
        "    or  \n"
        "  iguide %(prog)s -e <path/to/eval.rds> <options>"
    )

    description_str = str(
        "Generate a custom report from and evaluated iGUIDE output or specify "
        "config file(s) to use for generating a report."
    )
    
    parser = argparse.ArgumentParser(
        prog = "report",
        usage = usage_str,
        description = description_str
    )

    parser.add_argument(
        "-c", "--config", nargs = "*", default = None,
        help = str(
            "Run specific config file(s) in yaml format. Can specify more than "
            "one to combine several runs together for evaluation. Input in " 
            "in this format will 'evaluate' the data initially and generate " 
            "the respective report. The evaluation data object will be removed."
        ),
        metavar = "CONFIG_FILE"
    )

    parser.add_argument(
        "-e", "--evaldata", nargs = 1, default = None,
        help = str(
            "An evaluation dataset, in rds format. Can be generated by the "
            "'iguide eval' subcommand. Multiple runs and specific sample "
            "information can be included in the evaluation. See "
            "'iguide eval -h'."
        ),
        metavar = "EVAL_FILE"
    )

    parser.add_argument(
        "-o", "--output", nargs = 1, required = True,
        help = "Output report file, extention not required.",
        metavar = "OUTPUT"
    )

    parser.add_argument(
        "-s", "--support", nargs = 1, default = None,
        help = str(
            "Supporting data input, csv or tsv format. Only one file. Must "
            "have 'specimen' column and only specimens matching data in this "
            "column will be considered for evaluation and in the report."
        ),
        metavar = "SUPPORT"
    )

    parser.add_argument(
        "-f", "--figures", action="store_true",
        help = str(
            "Generate figures along with output report (pdf and png formats)."
        )
    )

    parser.add_argument(
        "-d", "--savedata", action="store_true",
        help = str(
            "Data to generate the report will be saved as an R image with "
            "output. Helpful for debuging templates."
        )
    )

    parser.add_argument(
        "-t", "--format", nargs = 1, choices=["pdf", "html"], default = "html",
        help = str(
            "Output format for report. Either 'pdf' or 'html' (default). "
            "Will append the appropriate extension to the output file name."
        ),
        metavar = "PDF_or_HTML"
    )

    parser.add_argument(
        "-g", "--graphic", action="store_true",
        help = "Includes an opening graphic on the report."
    )

    parser.add_argument(
        "--template", nargs = 1,
        default = "tools/rscripts/report_templates/iGUIDE_report_template.Rmd",
        help = "File path to standard or custom iGUIDE report template.",
        metavar = "RMD_FILE"
    )

    parser.add_argument(
        "-i", "--iguide_dir", 
        default = os.getenv("IGUIDE_DIR"),
        help = str(
            "Path to iGUIDE installation, do not change for normal "
            "applications."
        ),
        metavar = "IGUIDE_DIR"
    )
    
    # The remaining args will not be used
    args, remaining = parser.parse_known_args(argv)
    
    # iGUIDE directory
    iguide_directory = Path(args.iguide_dir)
    
    if not iguide_directory.exists():
        sys.stderr.write(
            "Error: could not find iGUIDE directory '{}'\n".format(
                args.iguide_dir))
        sys.exit(1)
    
    # iGUIDE report script(s)
    r_script = iguide_directory / "tools/rscripts/generate_iGUIDE_report.R"
    
    if not r_script.is_file():
        sys.stderr.write(
            "Error: Could not find a {0} in directory '{1}'\n".format(
                "generate_iGUIDE_report.R", args.iguide_dir + "/tools/rscripts/"
            )
        )
        sys.exit(1)

    if args.config is not None:
        eval_script = iguide_directory / "tools/rscripts/evaluate_incorp_data.R"
        if not eval_script.is_file():
            sys.stderr.write(
                "Error: Could not find a {0} in directory '{1}'\n".format(
                    "evaluate_incorp_data.R", args.iguide_dir + "/tools/rscripts/"
                )
            )
            sys.exit(1)
    
    r_template = iguide_directory / "".join(args.template)
    
    if not r_template.exists():
        r_template = Path(str(args.template))
        if not r_template.exists():
            sys.stderr.write(
                "Error: Could not find a report template: '{}'\n".format(
                    "".join(args.template)
                )
            )
            sys.exit(1)
    
    if not r_script.is_file():
        sys.stderr.write(
            "Error: Could not find a {0} in directory '{1}'\n".format(
                "generate_iGUIDE_report.R", args.iguide_dir + "/tools/rscripts/"
            )
        )
        sys.exit(1)

    
    # Decide processing method, prioritize '-e' over '-c'
    eval_first = False
    if args.config is not None:
        eval_first = True
    if args.evaldata is not None:
        eval_first = False

    # Evaluate first if required
    if eval_first:
        final_output = "".join(args.output)
        final_path = final_output.split("/")
        final_path.remove(final_path[len(final_path)-1])
        output_path = Path("/".join(final_path))
        temp_output = Path(output_path / "temp.eval.rds")
        
        if temp_output.exists():
            temp_output.unlink()
        
        eval_comps = ["Rscript", str(eval_script)]
        eval_comps = eval_comps + args.config + ["-o", str(temp_output)]
        
        if args.support is not None:
            eval_comps = eval_comps + ["-s"] + args.support
        
        eval_comps = eval_comps + ["--iguide_dir", str(iguide_directory)]
        
        eval_cmd = subprocess.run(eval_comps)
        
        if eval_cmd.returncode != 0:
            sys.stderr.write(
                "Error: Evaluation of input data did not exit with a 0 code. ",
                "Check for errors."
            )
            sys.exit(eval_cmd.returncode)
        
    # Generate report command
    ## Check for input eval file
    if eval_first:
        eval_input = str(temp_output)
    else:
        eval_input = "".join(args.evaldata)
    
    if not Path(eval_input).exists():
        sys.stderr.write(
            "Error: Could not find input evaluation data: {}".format(eval_input)
        )
        sys.exit(1)
    
    r_comps = ["Rscript", str(r_script)] + [eval_input, "-o"] + args.output
    if args.figures:
        r_comps.append("-f")
    if args.savedata:
        r_comps.append("-d")
    if args.graphic:
        r_comps.append("-g")
    r_comps = r_comps + ["--template", str(r_template)]
    r_comps = r_comps + ["--iguide_dir", str(iguide_directory)]

    cmd = subprocess.run(r_comps)

    if eval_first:
        temp_output.unlink()

    sys.exit(cmd.returncode)
