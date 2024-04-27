# Building my own git in python

## How to install

1. Install python version 3.10^

2. Download my-own-git and move it in /usr/local/bin

```bash
$ sudo mv [download folder]/my-own-git /usr/local/bin
```

3. Add the absolute path to my-own-git within the environment variable file, so that the 'wyag' script can be run at any location on the filesystem

```bash
$ echo "export PATH=$PATH:/usr/local/bin/my-own-git" >> ~/.bashrc
$ source ~/.bashrc
```
