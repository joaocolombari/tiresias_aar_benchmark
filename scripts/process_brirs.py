from tiresias_benchmark.cli import main

if __name__ == "__main__":
    main(["brir-process", *(__import__("sys").argv[1:])])
