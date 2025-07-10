# FileBuddy

![FileBuddy Icon](Images/Icon_Scaled.png)

FileBuddy is a utility Python script, intended to make quickly modifying, searching, and working with files easy.

## Usage

1. Make sure you have Python 3 installed.
2. Download the repository.
3. Add the Source directory within the repository to your system environment variables.
4. Open a terminal and run FileBuddy.

General form of command:

    fb <command> <options> [-p pattern] [-d directory] [-r recursive] [-o output] [-a hidden] [-v verbose] [-h help]

OR

    python fb.py <command> <options> [-p pattern] [-d directory] [-r recursive] [-o output] [-a hidden] [-v verbose] [-h help]

## Commands

Going in place of `<command>`.

| Command | Example | Description |
| --- | --- | --- |
| search | `fb search "\bPattern\b" -p "\.txt$"` | Searches the contents of files, using the given regex pattern. The regex pattern checks each line of all text files. |
| list | `fb list -r` | Lists the files and directories. |
| size | `fb size -a` | Lists the sizes of each file and directory. |
| rename | `fb rename "$(0).txt" -p "[a-z]+"` | Renames the files and directories. |
| delete | `fb delete -p ".*\.txt"` | Deletes the files and directories.
| copy | `fb copy "C:/destination" -p ".*\.txt"` | Copies the files and directories to the given destination path. |
| move | `fb move "C:/destination" -p ".*\.txt"` | Moves the files and directories to the given destination path. |

**Notes**

Only search, rename, copy and move use `<options>`.

For rename, copy, move, can use `$(N)` arguments in their destination names to references the groups from the `-p` regex pattern. For example, `$(0)` will be replaced with the whole pattern match, and `$(1)` will be replaced with the first capturing group, etc.

It is recommended to use `-a` with `size` to ensure you get the proper sizes of directires. Otherwise, hidden sub-directories and files are ignored, which may yield invalid results. 

## Flags

| Flag | Example | Description |
| --- | --- | --- |
| `-h`, `--help` | `-h` | Displays the help message. |
| `-p`, `--pattern` | `-p "\d+"` | Defines what regex pattern to use to filter the files and directories. Defaults to use all files and directories within the working directory. |
| `-d`, `--directory` | `-d "../Source"` | Defines the working directory. Defaults to `.`. |
| `-r`, `--recursive` | `-r` | If given, the operations on directories will be recursive. |
| `-o`, `--output` | `-o "log.txt"` | If given, all output will be redirected to a file. If not given, the output is printed in the terminal. |
| `-a`, `--all` | `-a` | Includes hidden directories and files in the search. |
| `-v`, `--verbose` | `-v` | Outputs additional information for some commands. |