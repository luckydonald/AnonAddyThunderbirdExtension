# base

Small reusable git base for other repositories.

This history is intentionally rooted at `empty/init` from `https://github.com/EmptyAAS/empty.git`. That gives multiple repos the same empty ancestor commit, which makes it possible to rebase or merge this base into another repo in a predictable way.

## Table of contents

<!-- TOC -->
* [base](#base)
  * [Table of contents](#table-of-contents)
* [Add This To Your Repo](#add-this-to-your-repo)
  * [What to do](#what-to-do)
    * [Which Workflow To Choose](#which-workflow-to-choose)
* [Installation](#installation)
  * [Setup](#setup)
  * [Setup: a) Checkout](#setup-a-checkout)
  * [Setup: b) Rebase Onto `base/mane`](#setup-b-rebase-onto-basemane)
  * [Setup: c) Merge `base/mane`](#setup-c-merge-basemane)
  * [After Adopting The Base](#after-adopting-the-base)
<!-- TOC -->

# Add This To Your Repo

## Overview
There are three ways to adopt this:

- start with it from the get-go, creating your branch from `base/mane`.
  - obviously only works if you haven't commited anything yet.
  - otherwise see rebase below, that's basically _"plz pretend I started from that and did all my own commits afterward!"_
- rebase your repo on top of `base/mane` if you want this base to become part of your linear history 
  - recommended if your git is not yet used by others
- merge `base/mane` into your repo if you do not want to rewrite history

If you only want a one-time copy of the files, just copy them manually. The steps below are for keeping your repo connected to this base over time.

### Which Workflow To Choose

Choose rebase if:

- you want this base to sit underneath your repo's commits
- you prefer a linear history
- force-pushing rewritten history is acceptable

Choose merge if:

- your branch is already published or shared
- you want the least disruptive adoption path
- you are fine with explicit merge commits for base updates


# Installation
## Setup

Add the remotes you need:

```bash
git remote add empty https://github.com/EmptyAAS/empty.git
git remote add base https://github.com/luckydonald/base.git
git fetch empty init
git fetch base mane
```

If your repository does not already descend from `empty/init`, and you are willing to rewrite its history, re-root it once:

```bash
git rebase --root --onto empty/init
```

That keeps your file history intact, but rewrites every commit in the branch so the new root is the shared empty commit.

## Setup: a) Checkout
todo

## Setup: b) Rebase Onto `base/mane`

Use this if you want a clean linear history, and you are comfortable rewriting your branch.

Initial adoption:

```bash
git rebase --onto base/mane empty/init
```

After that, future updates are just:

```bash
git fetch base
git rebase base/mane
```

Notes:

- resolve conflicts as they appear, then continue with `git rebase --continue`
- if you already pushed the branch, you will usually need `git push --force-with-lease`
- this is best for personal branches or repos where force-pushes are acceptable

## Setup: c) Merge `base/mane`

Use this if you want to preserve existing history and avoid rebasing published branches.

Initial adoption into an unrelated existing repo:

```bash
git merge --allow-unrelated-histories --no-ff base/mane
```

Future updates:

```bash
git fetch base
git merge --no-ff base/mane
```

Notes:

- this keeps a merge commit for each base update
- this is the safer choice for shared branches
- if your repo already shares `empty/init` as an ancestor, the initial `--allow-unrelated-histories` is not needed

## After Adopting The Base

Once the base is present in your repo, the files provided by this repo live in your repo like normal files. In particular, the `ai/scripts/*.sh` helpers are intended to be run from inside the consuming repository.
