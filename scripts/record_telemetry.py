from tiresias_benchmark.cli import main

if __name__ == "__main__":
    main(["telemetry-record", *(__import__("sys").argv[1:])])
