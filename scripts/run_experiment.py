from tiresias_benchmark.cli import main

if __name__ == "__main__":
    main(["experiment-run", *(__import__("sys").argv[1:])])
