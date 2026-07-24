import os
import sys
import subprocess
import tempfile
from dataclasses import dataclass

GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fb.py"))


class TestFailure(Exception):
    def __init__(self, expected: str, actual: str):
        super().__init__("Test assertion failed")
        self.expected = expected
        self.actual = actual


def normalize_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f.readlines()]


def run_fb(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, FB_PATH] + args
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def expect_equal(actual, expected):
    if actual != expected:
        raise TestFailure(repr(expected), repr(actual))


def expect_true(condition: bool, expected: str, actual: str):
    if not condition:
        raise TestFailure(expected, actual)


def ensure_success(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        expected = "Return code 0"
        actual = (
            f"Return code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
        raise TestFailure(expected, actual)


def write_file(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def setup_fixture(root: str):
    write_file(os.path.join(root, "test.txt"), "Hello world!\nHello cow!\nBye pig!\n")
    write_file(os.path.join(root, "notes.md"), "Notes line\n")
    write_file(os.path.join(root, "header.h"), "#pragma once\n")
    write_file(os.path.join(root, "folder2", "test"), "test\n")
    write_file(os.path.join(root, "folder2", "folder", "test"), "test\n")


@dataclass
class TestCase:
    test_id: str
    description: str
    func: callable


def test_list_recursive(root: str):
    result = run_fb(["list", "-d", ".", "-r", "-o", "out.txt"], root)
    ensure_success(result)
    actual = set(normalize_lines(os.path.join(root, "out.txt")))
    expected = {
        "./folder2/",
        "./test.txt",
        "./notes.md",
        "./header.h",
        "./folder2/folder/",
        "./folder2/test",
        "./folder2/folder/test",
    }
    expect_equal(actual, expected)


def test_search_file_filter(root: str):
    result = run_fb(["search", "Hello", "-p", r"\.txt$", "-d", ".", "-r", "-o", "out.txt"], root)
    ensure_success(result)
    actual = normalize_lines(os.path.join(root, "out.txt"))
    expected = [
        "./test.txt",
        "    1: Hello world!",
        "    2: Hello cow!",
    ]
    expect_equal(actual, expected)


def test_find_alias(root: str):
    s1 = run_fb(["search", "Hello", "-p", r"\.txt$", "-d", ".", "-r", "-o", "search.log"], root)
    s2 = run_fb(["find", "Hello", "-p", r"\.txt$", "-d", ".", "-r", "-o", "find.log"], root)
    ensure_success(s1)
    ensure_success(s2)
    actual = normalize_lines(os.path.join(root, "find.log"))
    expected = normalize_lines(os.path.join(root, "search.log"))
    expect_equal(actual, expected)


def test_extract_groups(root: str):
    result = run_fb(["extract", r"Hello (\w+)!", "-p", r"\.txt$", "-d", ".", "-r", "-o", "out.txt"], root)
    ensure_success(result)
    actual = normalize_lines(os.path.join(root, "out.txt"))
    expected = [
        "./test.txt",
        "    1:1: world",
        "    2:1: cow",
    ]
    expect_equal(actual, expected)


def test_search_format_content_only(root: str):
    result = run_fb([
        "search",
        r"(Hello \w+!)",
        "-p",
        r"\.txt$",
        "-d",
        ".",
        "-r",
        "--format",
        ">$0<",
        "-o",
        "out.txt",
    ], root)
    ensure_success(result)
    actual = normalize_lines(os.path.join(root, "out.txt"))
    expected = [
        "./test.txt",
        ">Hello world!<",
        ">Hello cow!<",
    ]
    expect_equal(actual, expected)


def test_list_format_paths(root: str):
    result = run_fb(["list", "-d", ".", "-r", "--format", "($0)", "-o", "out.txt"], root)
    ensure_success(result)
    actual = set(normalize_lines(os.path.join(root, "out.txt")))
    expected = {
        "(./folder2/)",
        "(./test.txt)",
        "(./notes.md)",
        "(./header.h)",
        "(./folder2/folder/)",
        "(./folder2/test)",
        "(./folder2/folder/test)",
    }
    expect_equal(actual, expected)


def test_output_file_excluded(root: str):
    result = run_fb(["list", "-d", ".", "-r", "-o", "out-check.txt"], root)
    ensure_success(result)
    lines = normalize_lines(os.path.join(root, "out-check.txt"))
    expect_true(
        "./out-check.txt" not in lines,
        "Output file path should not appear in command output",
        "\n".join(lines),
    )


def test_rename_groups(root: str):
    result = run_fb(["rename", "$1pp", "-p", r"^(.*)\.h$", "-d", ".", "-r", "-y", "-o", "out.txt"], root)
    ensure_success(result)
    expect_true(
        os.path.exists(os.path.join(root, "headerpp")) and not os.path.exists(os.path.join(root, "header.h")),
        "header.h renamed to headerpp",
        f"header.h exists={os.path.exists(os.path.join(root, 'header.h'))}, headerpp exists={os.path.exists(os.path.join(root, 'headerpp'))}",
    )


def test_replace_groups(root: str):
    result = run_fb([
        "replace",
        r"Hello (\w+)!",
        "Hi $1!",
        "-p",
        r"\.txt$",
        "-d",
        ".",
        "-r",
        "-y",
        "-o",
        "out.txt",
    ], root)
    ensure_success(result)
    with open(os.path.join(root, "test.txt"), "r", encoding="utf-8") as f:
        actual = f.read()
    expected = "Hi world!\nHi cow!\nBye pig!\n"
    expect_equal(actual, expected)


def test_copy_move_delete(root: str):
    r1 = run_fb(["copy", "$1_copy.txt", "-p", r"^(test)\.txt$", "-d", ".", "-r", "-y", "-o", "copy.txt"], root)
    ensure_success(r1)
    expect_true(
        os.path.exists(os.path.join(root, "test_copy.txt")),
        "test_copy.txt exists after copy",
        "test_copy.txt missing",
    )

    r2 = run_fb(["move", "$1_moved.md", "-p", r"^(notes)\.md$", "-d", ".", "-r", "-y", "-o", "move.txt"], root)
    ensure_success(r2)
    expect_true(
        os.path.exists(os.path.join(root, "notes_moved.md")) and not os.path.exists(os.path.join(root, "notes.md")),
        "notes.md moved to notes_moved.md",
        f"notes.md exists={os.path.exists(os.path.join(root, 'notes.md'))}, notes_moved.md exists={os.path.exists(os.path.join(root, 'notes_moved.md'))}",
    )

    r3 = run_fb(["delete", "-p", r".*_copy\.txt$", "-d", ".", "-r", "-y", "-o", "delete.txt"], root)
    ensure_success(r3)
    expect_true(
        not os.path.exists(os.path.join(root, "test_copy.txt")),
        "test_copy.txt removed by delete",
        "test_copy.txt still exists",
    )


def run_test_case(test_case: TestCase) -> bool:
    with tempfile.TemporaryDirectory(prefix="filebuddy_test_") as temp_dir:
        setup_fixture(temp_dir)
        try:
            test_case.func(temp_dir)
            print(f"{test_case.test_id} {GREEN}PASS{RESET}")
            return True
        except TestFailure as e:
            print(f"{test_case.test_id} {RED}FAIL{RESET}")
            print("Expected:")
            print(e.expected)
            print("Actual:")
            print(e.actual)
            return False
        except Exception as e:
            print(f"{test_case.test_id} {RED}FAIL{RESET}")
            print("Expected:")
            print("Test completes without unhandled exceptions")
            print("Actual:")
            print(repr(e))
            return False


def main() -> int:
    if not os.path.exists(FB_PATH):
        print(f"Could not find fb.py at {FB_PATH}")
        return 1

    tests = [
        TestCase("T001", "list recursive output", test_list_recursive),
        TestCase("T002", "search with -p filter", test_search_file_filter),
        TestCase("T003", "find alias equals search", test_find_alias),
        TestCase("T004", "extract capture groups", test_extract_groups),
        TestCase("T005", "search format applies to content", test_search_format_content_only),
        TestCase("T006", "list format applies to paths", test_list_format_paths),
        TestCase("T007", "-o output file excluded", test_output_file_excluded),
        TestCase("T008", "rename with $1 groups", test_rename_groups),
        TestCase("T009", "replace with $1 groups", test_replace_groups),
        TestCase("T010", "copy move delete flow", test_copy_move_delete),
    ]

    passed = 0
    for test_case in tests:
        if run_test_case(test_case):
            passed += 1

    total = len(tests)
    print(f"Summary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
