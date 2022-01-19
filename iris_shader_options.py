#!/usr/bin/env python3
from pyjavaproperties import Properties
from typing import Literal, NamedTuple, Union
from dataclasses import dataclass
from zipfile import Path as ZipPath
from pathlib import Path
from argparse import ArgumentParser
from sys import exit

ArgNamespace = NamedTuple("ArgNamespace", [("language_code", str), ("output_path", Union[Path, None, Literal[False]]), ("input_path", Path)])

def path_arg(path: str) -> Path:
    return Path(path)

def get_shaderpacks_path(input_path: Path) -> Path:
    if input_path.name == "shaderpacks":
        return input_path
    elif input_path.name == ".minecraft":
        return Path(input_path, "shaderpacks")
    else:
        return Path(input_path, ".minecraft/shaderpacks")

def get_properties(path: Path) -> Properties:
    properties = Properties()
    properties.load(path.open("r"))
    return properties

@dataclass
class ScreenProperty:
    screen_names: set
    options: set

def parse_screen_property(screen_property: str) -> ScreenProperty:
    parts = screen_property.split()
    screen_names = set()
    options = set()
    for part in parts:
        if part[0] == "[" and part[-1] == "]":
            screen_names.add(part[1:-1])
        elif not (part[0] == "<" and part[-1] == ">"):
            options.add(part)
    return ScreenProperty(screen_names, options)

def get_shader_options_readable(shader_lang: str, shader_options_path: Path) -> str:
    shader_base_path = shader_options_path.with_suffix("")

    if shader_base_path.is_dir():
        path_type = Path
    elif shader_base_path.is_file() and shader_base_path.suffix == ".zip":
        path_type = ZipPath
    else:
        raise ValueError(f"No shader for config [{shader_base_path.name}]")
    
    try:
        shader_options_properties = get_properties(shader_options_path)
    except:
        raise ValueError(f"No valid shader options file for shader [{shader_base_path.name}]")

    try:
        shader_lang_properties = get_properties(path_type(shader_base_path, f"shaders/lang/{shader_lang}.lang"))
    except:
        shader_langs = ', '.join(lang_path.name.rstrip(".lang") for lang_path in path_type(shader_base_path, "shaders/lang/").iterdir() if lang_path.name.endswith(".lang"))
        raise ValueError(f"No valid language file for [{shader_lang}] in shader [{shader_base_path.name}]\nAvailable languages: {shader_langs}")

    try:
        shader_properties = get_properties(path_type(shader_base_path, "shaders/shaders.properties"))
    except:
        raise ValueError(f"No valid properties file for shader [{shader_base_path.name}]")
    
    screen_properties: dict[str, ScreenProperty] = {prop.lstrip("screen."): parse_screen_property(val) for prop, val in shader_properties.getPropertyDict().items() if prop.startswith("screen.")}
    screen_screen_names: dict[str, str] = {screen_name: prop for prop, val in screen_properties.items() for screen_name in val.screen_names}
    option_screen_names: dict[str, str] = {option: prop for prop, val in screen_properties.items() for option in val.options}

    def get_screen_path(screen_name: str) -> str:
        lang_screen_name: str = shader_lang_properties.getProperty(f"screen.{screen_name}")
        parent_screen_name = screen_screen_names.get(screen_name)
        return lang_screen_name if parent_screen_name is None else f"{get_screen_path(parent_screen_name)} -> {lang_screen_name}"

    return "".join(f"{shader_lang_properties.getProperty(f'option.{prop}')} ({get_screen_path(option_screen_names[prop])}): {val}\n" for prop, val in shader_options_properties.getPropertyDict().items())

def main() -> None:
    parser = ArgumentParser(description="Parse Iris shader options files and output in a human readable format")
    parser.add_argument("-l", "--lang", metavar="language_code", dest="language_code", default="en_US", help="The language code to use")
    parser.add_argument("-o", "--output", metavar="output_path", dest="output_path", nargs="?", const=None, default=False, type=path_arg, help="The path to the output file or directory")
    parser.add_argument("input_path", type=path_arg, help="The path to the Iris shader options file or Minecraft installation directory")
    args: ArgNamespace = parser.parse_args()
    if args.input_path.is_dir():
        for shader_options_path in get_shaderpacks_path(args.input_path).glob("*.txt"):
            try:
                output = get_shader_options_readable(args.language_code, shader_options_path)
                if args.output_path is False:
                    print(f"{shader_options_path.with_suffix('').name}\n{output}")
                elif args.output_path is None:
                    shader_options_path.with_stem(f"{shader_options_path.stem}_readable").write_text(output)
                else:
                    args.output_path.mkdir(parents=True, exist_ok=True)
                    Path(args.output_path, f"{shader_options_path.stem}_readable.txt").write_text(output)
            except ValueError as err:
                print(err)
    elif args.input_path.is_file():
        try:
            output = get_shader_options_readable(args.language_code, args.input_path)
            if args.output_path is False:
                print(output)
            elif args.output_path is None:
                args.input_path.with_stem(f"{args.input_path.stem}_readable").write_text(output)
            else:
                args.output_path.write_text(output)
        except ValueError as err:
            print(err)
            exit(1)
    else:
        print(f"Invalid input path [{args.input_path}]")
        exit(1)

if __name__ == "__main__":
    main()
