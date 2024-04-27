import argparse
import collections
import configparser
from datetime import datetime
import grp, pwd
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re       # regex
import sys      # need this in order to access command-line arguments (in sys.argv)
import zlib     # git compresses everything using zib


# ArgumentParser instance
argparser = argparse.ArgumentParser(description="A random description...")

# This line allows us to add commands when we call the script
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")

# Is mandatory to specify at least a command, for instance when we call
# git we need to give at least one command, we don't write only 'git'
argsubparsers.required = True  


# Add the 'init' argument 
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")

# Add the value 'path' for the argument 'init'
argsp.add_argument("path", metavar="directory", nargs="?", default=".", help="Where to create the repository.")


def main(argv=sys.argv[1:]):

    args = argparser.parse_args(argv)

    match args.command:
        case "add"          : cmd_init(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")


# Bridge function for the command init
def cmd_init(args):
    repo_create(args.path)



class GitRepository (object):

    worktree = None     # path of the effective working directory
    gitdir = None       # .git dir path, (it is located in the root of the working directory)
    conf = None         # .ini file path for config

    def __init__(self, path, force=False):
        
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a Git repository %s" % path)

        # --- Read configuration file in .git/config ---

        # self.conf is now an instance of the class ConfigParser        
        self.conf = configparser.ConfigParser()

        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])

        elif not force:
            raise Exception("Configuration file missing")
        
        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)


def repo_file(repo, *path, mkdir=False):
    """Same as repo_path, but create dirname(*path) if absent.  For
example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
.git/refs/remotes/origin."""

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)
    

def repo_dir(repo, *path, mkdir=False):
    """Same as repo_path, but mkdir *path if absent if mkdir."""

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception("Not a directory %s" % path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None

    
def repo_path(repo, *path):
    """Compute path under repo's gitdir."""
    return os.path.join(repo.gitdir, *path)


def repo_create(path):

    repo = GitRepository(path, True)

    # First, we make sure the path either doesn't exist or is an empty dir.

    if (os.path.exists(repo.worktree)):

        if not (os.path.isdir(repo.worktree)):
            raise Exception("Not a directory %s" % path)
        
        # in this case .git exists (inside the worktree) and it is not empty
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception("Not a directory %s" % path)
    else:
        os.makedirs(repo.worktree)


    # Create all the subdirs of .git and assert "created"
    assert repo_dir(repo, "branches", mkdir=True)  
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)


    # create .git/description and write ctx in it 
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

    # create .git/HEAD and write ctx in it
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    #create .git/config and write the default config in it
    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo
    
def repo_default_config():

    # ret is now an instance of the class ConfigParser
    ret = configparser.ConfigParser()

    ret.add_section("core")

    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    # file preview result: (config)  

        # [core]                        (this is a section)
        # repositoryformatversion = 0   
        # filemode = false
        # bare = false

    # (.ini files are human readable and are simple text file with the .ini extension
    # in order to read them correctly) 

    # ret is an object that rappresent the defaul configuration,
    # and can be written in an .ini file in a "dictionary format"  

    return ret 
    
 # _
