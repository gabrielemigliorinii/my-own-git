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


# Global vars
# ------------------------------------------------------------------------------------

# ArgumentParser instance
argparser = argparse.ArgumentParser(description="A random description...")

# This line allows us to add commands when we call the script
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")

# Is mandatory to specify at least a command, for instance when we call
# git we need to give at least one command, we don't write only 'git'
argsubparsers.required = True  




# Add 'init' command 
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")

# Add the value 'path' for the argument 'init'
argsp.add_argument("path", metavar="directory", nargs="?", default=".", help="Where to create the repository.")




# Add 'cat-file' command
argsp = argsubparsers.add_parser("cat-file", help="Provide content of repository objects")

# Add the value 'type' for the argument 'cat-file'
argsp.add_argument("type", metavar="type", choices=["blob", "commit", "tag", "tree"], help="Specify the type")

# Add the value 'object' (a SHA1 hex string) for the argument 'cat-file', SHA1
argsp.add_argument("object", metavar="object", help="The object to display")




argsp = argsubparsers.add_parser("hash-object", help="Compute object ID and optionally creates a blob from a file")

argsp.add_argument("-t", metavar="type", dest="type", choices=["blob", "commit", "tag", "tree"], default="blob", help="Specify the type")

argsp.add_argument("-w", dest="write", action="store_true", help="Actually write the object into the database")

argsp.add_argument("path", help="Read object from <file>")




argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")

argsp.add_argument("commit", default="HEAD", nargs="?", help="Commit to start at.")


# ------------------------------------------------------------------------------------


def main(argv=sys.argv[1:]):

    args = argparser.parse_args(argv)

    match args.command:
        case "add"          : cmd_add(args)
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



# -----------------------------------------------------------------------------------------
# Begin bridge functions


def cmd_init(args):
    repo_create(args.path)

def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())

def cmd_hash_object(args):
    
    if args.write:
        repo = repo_find()
    else:
        repo = None

    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)


def cmd_log(args):

    repo = repo_find()

    print("digraph mygitlog{")
    print("  node[shape=rect]")
    
    log_graphviz(repo, object_find(repo, args.commit), set())
    
    print("}")

# End bridge functions
# -----------------------------------------------------------------------------------------



# -----------------------------------------------------------------------------------------
# Begin classes


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

class GitObject (object):

    def __init__(self, data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, repo):
        """This function MUST be implemented by subclasses.
        
It must read the object's contents from self.data, a byte string, and do
whatever it takes to convert it into a meaningful representation.  What exactly that means depend on each subclass."""
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

    def init(self):
        pass # Just do nothing. This is a reasonable default!

class GitBlob (GitObject):

    fmt = b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data

class GitCommit (GitObject):
    
    fmt = b'commit'

    def deserialize(self, data):
        self.commit = commit_parse(data)

    def serialize(self):
        return commit_serialize(self.commit)

    def init(self):
        self.commit = dict()


class GitTreeLeaf (object):

    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha

class GitTree(GitObject):
    fmt=b'tree'

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items = list()


# End classes
# -----------------------------------------------------------------------------------------




# -----------------------------------------------------------------------------------------
# Begin utilities 

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
    

# Find the root of the current repository
def repo_find(path=".", required=True):

    # relative to absolute path
    path = os.path.realpath(path)

    # if we are in the root (bacause we've found .git repo), return an instance of the class GitRepository
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    # If we haven't returned, recurse in parent, if w
    parent = os.path.realpath(os.path.join(path, ".."))

    # If the parent is equals to path, we are already in the root dir, and .git is missing
    if parent == path:
        # Bottom case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root.
        if required:
            raise Exception("No git directory.")
        else:
            return None

    # Recursive case
    return repo_find(parent, required)

def object_read(repo, sha):

    path = repo_path(repo, "objects", sha[0:2], sha[2:])

    if not os.path.isfile(path):
        return None

    with open(path, "rb") as f:

        # every object is compressed with zlib
        raw = zlib.decompress(f.read())

        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))

        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        # Pick constructor
        match fmt:
            case b'commit' : c=GitCommit
            case b'tree'   : c=GitTree
            case b'tag'    : c=GitTag
            case b'blob'   : c=GitBlob
            case _:
                raise Exception("Unknown type {0} for object {1}".format(fmt.decode("ascii"), sha))

        # Call constructor and return object
        return c(raw[y+1:])


def object_write(obj, repo=None):

    # Serialize object data
    data = obj.serialize()

    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        # Compute path
        path=repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)

        if not os.path.exists(path):
            with open(path, 'wb') as f:
                # Compress and write
                f.write(zlib.compress(result))
    return sha

def cat_file(repo, sha, fmt=None):

    obj = object_read(repo, object_find(repo, sha, fmt=fmt))
    
    if obj == None:
        print("Not a valid object name: %s" % sha)
        return
        
    sys.stdout.buffer.write(obj.serialize())

# Temp function that has to be implemented. Now it returns just 'name' (SHA1 hex string)
def object_find(repo, name, fmt=None, follow=True):
    return name


def object_hash(fd, fmt, repo=None):
    """ Hash object, writing it to repo if provided."""
    data = fd.read()

    # Choose constructor according to fmt argument
    match fmt:
        case b'commit' : obj=GitCommit(data)
        case b'tree'   : obj=GitTree(data)
        case b'tag'    : obj=GitTag(data)
        case b'blob'   : obj=GitBlob(data)
        case _: raise Exception("Unknown type %s!" % fmt)

    return object_write(obj, repo)



def commit_parse(raw, start=0, dct=None):
    
    if not dct:
        dct = collections.OrderedDict()

        # You CANNOT declare the argument as dct=OrderedDict() or all
        # call to the functions will endlessly grow the same dict.

            # Not sure about that

    # We search for the next space and the next newline.
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # If space appears before newline, we have a keyword.  Otherwise,
    # it's the final message, which we just read to the end of the file.



    # Base case
    # =========
    # If newline appears first (or there's no space at all, in which
    # case find returns -1), we assume a blank line.  A blank line
    # means the remainder of the data is the message.  We store it in
    # the dictionary, with None as the key, and return.

    if (spc < 0) or (nl < spc):

        assert nl == start
        dct[None] = raw[start+1:]
        return dct

    # Recursive case
    # ==============
    # we read a key-value pair and recurse for the next.
    key = raw[start:spc]

    # Find the end of the value.  Continuation lines begin with a
    # space, so we loop until we find a "\n" not followed by a space.
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '): break

    # Grab the value
    # Also, drop the leading space on continuation lines
    value = raw[spc+1:end].replace(b'\n ', b'\n')

    # Don't overwrite existing data contents
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [ dct[key], value ]
    else:
        dct[key]=value

    return commit_parse(raw, start=end+1, dct=dct)

def commit_serialize(commit):

    ret = b''

    # Output fields
    for k in commit.keys():
        # Skip the message itself
        if k == None: continue
        val = commit[k]
        # Normalize to a list
        if type(val) != list:
            val = [ val ]

        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    # Append message
    ret += b'\n' + commit[None] + b'\n'

    return ret


def log_graphviz(repo, sha, seen):

    if sha in seen:
        return
    
    seen.add(sha)

    commit = object_read(repo, sha)
    short_hash = sha[0:8]
    message = commit.commit[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    if "\n" in message: # Keep only the first line
        message = message[:message.index("\n")]

    print("  c_{0} [label=\"{1}: {2}\"]".format(sha, sha[0:7], message))
    assert commit.fmt==b'commit'

    if not b'parent' in commit.commit.keys():
        # Base case: the initial commit.
        return

    parents = commit.commit[b'parent']

    if type(parents) != list:
        parents = [ parents ]

    for p in parents:
        p = p.decode("ascii")
        print ("  c_{0} -> c_{1};".format(sha, p))
        log_graphviz(repo, p, seen)


# Example of a tree object leaf: [mode] 0x20 [path] 0x00 [sha-1]
def tree_parse_one(raw, start=0):

    # Find the space terminator (0x20) of the mode
    mode_len = raw.find(b' ', start)
    
    # the mode's length must be 5 or 6
    assert mode_len-start == 5 or mode_len-start==6

    # Read the mode
    mode = raw[start:mode_len]

    if len(mode) == 5:
        # Normalize to six bytes.
        mode = b" " + mode

    # Find the NULL terminator of the path
    path_len = raw.find(b'\x00', mode_len)

    # and read the path
    path = raw[mode_len+1 : path_len]

    # Read the SHA and convert to a hex string
    sha = format(int.from_bytes(raw[path_len+1 : path_len+21], "big"), "040x")

    return path_len+21, GitTreeLeaf(mode, path.decode("utf8"), sha)


# “real” parser which just calls the previous one in a loop, until input data is exhausted.
def tree_parse(raw):

    pos = 0
    max = len(raw)
    ret = list()
    
    while pos < max:
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)

    return ret



# Notice this isn't a comparison function, but a conversion function.
# Python's default sort doesn't accept a custom comparison function,
# like in most languages, but a `key` arguments that returns a new
# value, which is compared using the default rules.  So we just return
# the leaf name, with an extra / if it's a directory.

def tree_leaf_sort_key(leaf):
    
    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return leaf.path + "/"


def tree_serialize(obj):

    # This function sorts the tree object by the path of the leafs (read tree_leaf_sort_key() function)
    obj.items.sort(key=tree_leaf_sort_key)
    
    ret = b''
    
    for i in obj.items:
        
        ret += i.mode
        ret += b' '
        ret += i.path.encode("utf8")
        ret += b'\x00'
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")

    return ret






# End utilities
# -----------------------------------------------------------------------------------------
