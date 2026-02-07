import sys

def greeting(name):
    print(f"Hey {name}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: rocket-cli <name>")
        sys.exit(1)
    name = sys.argv[1]
    greeting(name)
