# M2Immoneuf plugin

Search and compare new-build homes and lands in France from the catalogue of M2's partner developers, directly from Claude (and ChatGPT).

The plugin bundles one remote MCP server and two skills. It runs no local code, installs no package and reads no credential or environment variable.

## What it connects to

| Component | Where | What it does |
| --- | --- | --- |
| MCP server `m2immoneuf` | `https://app-promoters.m2agent.co/mcp` (HTTPS, no authentication) | Catalogue search, home and development details, comparison, availability, map |
| Skill `consulter-le-catalogue` | `skills/consulter-le-catalogue/` | How to search, compare, check availability and prepare a callback request |
| Skill `comparer-programmes-et-lieux` | `skills/comparer-programmes-et-lieux/` | How to compare developments and show them on a map |

## MCP tools

`search_lots`, `list_cities`, `get_lot`, `get_program`, `compare_lots`, `compare_programs`, `show_programs_map`, `check_availability` and `create_lead`.

## Data sent to the server

- Search criteria written in the chat (city, budget, size, outdoor space, delivery date), and the AI assistant used. They are stored without any identity for 180 days.
- Only when the user explicitly agrees, for one request at a time: first name, last name, email, phone, the home concerned and the optional message, budget, project and callback time. They are forwarded to the partner developer's sales adviser, or to M2.

Nothing else leaves the conversation. Reservations and payments are not supported. Full details: [privacy policy](https://www.m2agent.co/politique-de-confidentialite) and [terms](https://www.m2agent.co/conditions-generales).

## Install

Once published, install it from the Claude plugin directory. To try this repository locally, clone it and run:

```bash
claude --plugin-dir .
```

## Repository layout

```
.claude-plugin/plugin.json   Claude manifest (source of truth for name and version)
.mcp.json                    Remote MCP server declaration for Claude
skills/                      Skills shared by Claude and ChatGPT
assets/logo.png              Logo
openai/                      plugin.json and mcp.json of the ChatGPT / OpenAI package
scripts/plugin.py            Local pre-submission check and ZIP builder (Python 3, standard library only)
tests/                       Tests of scripts/plugin.py
```

`scripts/plugin.py` and `tests/` are development tools: they are never loaded by Claude and never part of the ZIP.

## Check and package

```bash
python3 scripts/plugin.py check                 # Claude pre-submission checklist
python3 scripts/plugin.py build                 # check, then dist/m2immoneuf-<version>.zip
python3 scripts/plugin.py build --bump patch    # raise the version in both manifests first
python3 scripts/plugin.py build --force         # overwrite an existing zip
python3 -m unittest discover tests              # tests
```

`check` mirrors the [Claude pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist) and also runs `claude plugin validate .` when the Claude CLI is installed. `build` produces the ZIP uploaded on the OpenAI platform: a `m2immoneuf/` root folder with `plugin.json`, `mcp.json`, `assets/` and `skills/`.

## License

[MIT](LICENSE)
