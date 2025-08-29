# avosoft/avosoft_data_engine/cli.py
import argparse, os
from .services.orchestrator import Orchestrator

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", dest="ds", help="YYYY-MM-DD", default=None)
    args = ap.parse_args()
    if args.ds:
        os.environ["SIM_DATE"] = args.ds
    Orchestrator().run()

if __name__ == "__main__":
    main()
