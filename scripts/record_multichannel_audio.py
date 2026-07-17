from tiresias_benchmark.cli import main


if __name__ == "__main__":
    main(["exp02-record-test-sweep", *(__import__("sys").argv[1:])])
