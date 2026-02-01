#!/usr/bin/env python3
import json
import sys
import os
import subprocess
import argparse
from pathlib import Path
import platform

parser = argparse.ArgumentParser(
 prog="Sidechat MCP server",
 description="access tools in the os",
 epilog="USE IT WITH RESPONSABILITY"
)

parser.add_argument('-P','--valid_paths',nargs='*',default=[],help="Allowed paths, be responsible!")

args = parser.parse_args()

VALID_PATHS = [Path(p).expanduser() for p in args.valid_paths]
VALID_PATHS.sort(key=lambda p: len(p.parts), reverse=True)

CONFIG=".config"
if platform.system() == "Darwin":
 CONFIG="Library/Application Support"

memfile=Path(f"~/{CONFIG}/sidechat").expanduser() / "memories.json"

def rpc(data):
 print(json.dumps({"jsonrpc": "2.0", "result": data}), flush=True)

for res in sys.stdin: 
 input_data = json.loads(res)
 if input_data['method'] == 'initialize':
     rpc({
         "protocolVersion":"2024-11-05",
         "capabilities": {
             "tools":{"listChanged":True},"resources":{"listChanged":True},"completions":{}
         },
         "serverInfo":{"name":"demo", "version":"1.0.0"}
     })

 if input_data['method'] == 'tools/call':
     params = input_data.get('params')
     tool_name = params['name']
     args = params.get('arguments', {})
     break

 if input_data['method'] == 'notifications/initialized':
     rpc({})

 if input_data['method'] == 'tools/list':
     rpc({
          "tools": [
            {
                "name": "list_files",
                "description": "List files in directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string", 
                            "description": "Directory path (relative to valid paths)"
                        }
                    }
                }
            },
            {
                "name": "read_file", 
                "description": "Read file contents",
                "inputSchema": {
                    "type": "object", 
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (relative to valid paths)"
                        },
                        "filename": {
                            "type": "string",
                            "description": "File name to read"
                        }
                    },
                    "required": ["filename"]
                }
            }
            ]
         })


if tool_name == "list_files":
 valid_path = False
 DIR = Path(args.get('path') or '.').expanduser()
 for valid in VALID_PATHS:
     if DIR.is_relative_to(valid):
         valid_path = True
         rpc([f.name for f in DIR.glob("*")])
         break

 if not valid_path:
     rpc({
         "ok": False,
         "error": str("Path is not valid"),
         "path": str(DIR)
         })

elif tool_name == "read_file":
 file_path = Path(args.get('path') or '.').expanduser() / args.get('filename')
 valid_path = False
 for valid in VALID_PATHS:
     if file_path.is_relative_to(valid):
         valid_path = True
         try:
             with open(file_path, 'r') as f:
                 lines = f.readlines()
             
             formatted_lines = []
             for i, line in enumerate(lines, 1):
                 formatted_lines.append(f"<line number={i}>{line}</line>")
             
             rpc("".join(formatted_lines))
         except Exception as e:
             rpc({
                 "ok": False,
                 "error": str(e),
                 "path": str(file_path)
             })
         break

 if not valid_path:
     rpc({
         "ok": False,
         "error": str("Path is not valid"),
         "path": str(file_path)
         })


elif tool_name == "read_man_section":
 rpc(subprocess.run(
     ["mansnip", "--llm", args['manpage'], args['section']],
     stdout=subprocess.PIPE,
     stderr=subprocess.PIPE,
     text=True,
     check=False      
 ).stdout)

elif "memory" in tool_name:
 fd = os.open(memfile, os.O_RDONLY | os.O_CREAT, mode=0o644)
 with os.fdopen(fd, 'r') as f:
     try:
         mems = json.load(f)
     except:
         mems = []

 if tool_name == "show_memory":
     rpc(mems)

 # this is save memory
 else:
     mems.append(args.get('memory'))
     with open(memfile, 'w') as f:
         json.dump(mems,f, indent=2)

     rpc({"ok": True})


