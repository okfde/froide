#!/usr/bin/env python3

import re
import tomllib

import yaml


def main():
    def python_to_js(python_package: str) -> str | None:
        if python_package == "django-filingcabinet":
            return "@okfde/filingcabinet"

        if python_package.startswith("froide"):
            return python_package.replace("-", "_")

    uv_commit_re = re.compile(r"#([0-9a-f]+)$")
    pnpm_commit_re = re.compile(r"tar\.gz\/([0-9a-f]+)")

    with (
        open("uv.lock", "rb") as uv_lock_fd,
        open(file="pnpm-lock.yaml", mode="r") as pnpm_lock_fd,
    ):
        pnpm_docs = yaml.load_all(pnpm_lock_fd, yaml.SafeLoader)

        pnpm_lock = list(pnpm_docs)[-1]

        npm_packages = pnpm_lock["importers"]["."]["dependencies"]

        uv_lock = tomllib.load(uv_lock_fd)

        for python_module in uv_lock["package"]:
            if "git" not in python_module["source"]:
                continue

            python_module_name = python_module["name"]
            npm_package_name = python_to_js(python_module_name)

            if not npm_package_name:
                continue

            print("checking", python_module_name)

            python_version = uv_commit_re.search(python_module["source"]["git"])
            assert python_version
            python_version = python_version.group(1)

            npm_version = pnpm_commit_re.search(
                npm_packages[npm_package_name]["version"]
            )
            assert npm_version
            npm_version = npm_version.group(1)

            assert npm_version == python_version, (
                f"{python_module_name} versions differ in uv.lock and pnpm-lock.yaml ({python_version[:8]} vs. {npm_version[:8]}). Run `make dependencies` to fix this."
            )


if __name__ == "__main__":
    main()
