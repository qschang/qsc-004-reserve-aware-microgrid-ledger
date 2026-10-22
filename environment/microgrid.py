#!/usr/bin/env python3
import json, sys

# Starter workspace: implement the public contract described in instruction.md.
# The default starter intentionally refuses to publish a dispatch result.
def main():
    if len(sys.argv) != 3:
        return 2
    print("starter implementation incomplete", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
