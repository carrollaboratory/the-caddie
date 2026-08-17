## Welcome to the {program} Access Model 🚀

This repository serves as a downstream model designed to specialize the
[Common Access Model](https://github.com/include-dcc/common-access-model). The
structural foundation of this project is maintained and version-controlled via a
Git submodule containing the core schema.

The purpose of this model is to build out a program-specific extension (or
profile) by importing the core elements and layering the {program} unique data
requirements on top.

## Key Integration Guidelines

- Do Not Modify the Submodule from within this repository: All foundational
  classes, slots, and enums live in the core submodule. Any program-specific
  customizations must happen strictly in your downstream files.
- Leverage Imports: At this time, the current model imports the
  common_access_model.yaml directly within the main model definition.
- Extend via Inheritance: Use the is_a or mixins keys to create program-specific
  subclasses that inherit core slots while allowing you to add local attributes.
- Refine via Slot Usage: If you need to restrict or change the behavior of an
  inherited core slot just for your program's classes, use the slot_usage
  feature.

## Getting Started

If you aren't already familiar with working with submodules, there are just a
couple of key takeaways to keep in mind:

- The submodule has been pinned to a specific git commit hash to avoid
  unexpected changes the CAM creeping into downstream model interfering with
  local builds, CI/CD scripts, etc.
- The submodule itself should only be updated by deliberate action with the
  expectation that downstream model changes may be required to reflect incoming
  updates.

### Initializing the submodule

Before you can actually compile the model on a new machine, you'll need to pull
the submodule's content down. A convenient just recipe has been created for
exactly that:

```bash
just init-submodule
```

or, if you prefer to do it directly yourself:

```bash
git submodule update --init --recursive
# make sure nothing is broken
just lint && just test
```

Subsequent calls can drop the init if you know for a fact that no other
submodules have been added. The just recipe does call the linter and runs the
linkml test as a subsequent depenendency, in case there are upstream changes
that invalidate the downstream model.

### Updating the pinned hash

Once it has been decided that it is time to update the CAM to use the latest
version, the maintainer should run the following commands to fetch, test and
lock the new version into the downstream model's main.

```bash
# Navigate into the submodule directory
cd src/kf_access_model/schema/common_access_model

# Fetch and check out the desired remote target (e.g., main branch)
git fetch origin
git checkout origin/main

# Move back to the repository root
cd -

# Run linter and tests
just lint && just test


# Commit the new submodule hash pointer to this repository
git add src/kf_access_model/schema/common_access_model
git commit -m "chore: update common_access_model submodule to latest hash"
```
