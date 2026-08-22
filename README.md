# REapk OBB Builder
EN:

> **AI Authorship Disclaimer:** This project was created completely by an artificial intelligence agent. Human review, testing, and independent validation are recommended before using it in production or with software for which you do not have authorization.

PT_BR:

> **Disclaimer de autoria por IA:** Este projeto foi criado completamente por um agente de inteligência artificial. Recomenda-se revisão humana, testes e validação independente antes de utilizá-lo em produção ou com software para o qual você não tenha autorização.

## English

### Overview

This repository contains a Python program for inspecting an APK or XAPK/APKS bundle, locating a matching Unity expansion file (OBB), and packaging that OBB into the APK using the verified native APIs of REapk 0.1.1.

The repository `JRBusiness/REapk`, tag `v0.1.1` (`8dafd5a`), was inspected before implementation. The verified API supports manifest reading, DEX inspection, replacement of existing method bodies, aligned ZIP reconstruction, and native APK signing. It does **not** expose a supported API for declaring a new class or method or for updating `class_data` with a new startup method.

For that reason, `build.py` refuses to emit a supposedly standalone APK by default. The explicit `--no-inject` mode packages the OBB for testing and inspection, but does not extract it automatically at application startup.

### Requirements and setup

Use Python 3.10 or newer in a virtual environment:

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'reapk @ git+https://github.com/JRBusiness/REapk.git@v0.1.1'
```

The script does not call apktool, smali, baksmali, Java, zipalign, apksigner, or keytool.

### Usage

```bash
python build.py input/game.apk
python build.py input/game.xapk
python build.py input/game.apk --obb path/to/main.1435.com.example.game.obb
```

The commands above deliberately stop with a capability error before producing an APK. To test only the packaging operation, use the explicit opt-in flag:

```bash
python build.py input/game.xapk --no-inject
```

The default output is `output/game-standalone.apk`. Despite the filename, an artifact produced with `--no-inject` is not standalone. It is signed with the key cached by REapk under `~/.reapk/`; because this is not the original application's signing key, the artifact is intended for clean installation and testing, not for updating an installation signed by a different key.

### Detection and validation

For XAPK/APKS/ZIP inputs, the script reads `manifest.json` when present, locates APK and OBB members, and selects the base APK. Bundles with multiple APKs that appear to be split, architecture, or configuration APKs are rejected because REapk 0.1.1 does not merge splits.

The binary manifest is inspected through `apk.manifest.info`. An OBB must use the standard basename `main.<versionCode>.<package>.obb` or `patch.<versionCode>.<package>.obb`. The filename is checked against the package and `versionCode` from the APK, and empty OBB files are rejected. If both main and patch candidates are available, the main candidate is preferred.

When packaging is enabled, the OBB is stored as `assets/obb/<obb-filename>`. The current implementation does not copy it to `/sdcard/Android/obb/<package>/` because that requires a startup DEX hook that REapk 0.1.1 cannot safely declare through its verified API.

### Verified REapk 0.1.1 APIs

| API | Actual signature | Use |
|---|---|---|
| `reapk.Apk` | `Apk.from_bytes(data: bytes, label: str = "<bytes>") -> Apk`; `Apk.open(path: str) -> Apk`; `apk.manifest.info -> dict` | Open an APK/base APK and obtain `package`, `versionCode`, `versionName`, `minSdk`, and `targetSdk`. |
| `reapk.DexFile` | `DexFile(data: bytes)`; `classes()`; `class_methods(cdata_off)`; `find_method(class_desc, mname)` | Inspect existing classes and methods. |
| `reapk.disassemble` | `disassemble(dex, code_off)` | Disassemble an existing method body. |
| `reapk.assemble` | `assemble(asm, lines)` | Assemble smali against existing pools. |
| `reapk.assemble_interned` | `assemble_interned(dex, lines) -> (Interner, list[int])` | Assemble a replacement body and intern new references. |
| `reapk.build_code_item` | `build_code_item(regs, ins, outs, words) -> bytes` | Create a `code_item` for a replacement body. |
| `reapk.build_dex` | `build_dex(dex, replacements=None, add_strings=None, interner=None) -> bytes` | Re-emit DEX, primarily replacing bodies of already-declared methods. |
| `reapk.read_zip_entries` | `read_zip_entries(data: bytes) -> list[dict]` | Read ZIP entries while preserving payload and metadata. |
| `reapk.stored_entry` | `stored_entry(name: str, data: bytes) -> dict` | Create an uncompressed ZIP entry. |
| `reapk.write_aligned_zip` | `write_aligned_zip(entries: list[dict]) -> bytes` | Rebuild the ZIP and align stored entries. |
| `reapk.apk_sign_v2` | `apk_sign_v2(apk_bytes: bytes) -> bytes` | Add native APK Signature Scheme v2+v3 signing. |

`Interner` manages constant-pool entries but does not add declarations to DEX `class_data`. `DexFile.patch_return()` only forces a return in an existing method and does not create a startup hook.

### Why startup injection is not implemented

The full requested behavior would require inserting a call into `Application.onCreate()` or an Activity startup method and declaring a Dalvik helper that uses `AssetManager`, `File`, `mkdirs()`, and file streams to copy and verify the OBB. In REapk 0.1.1, `build_dex()` accepts replacements keyed by existing `code_off` values and remaps pools; `assemble_interned()` assembles instructions but does not create a class or insert a method into `class_data`. The package also has no native Java/Kotlin compiler for generating such a helper.

Inventing an API or editing `class_data` outside a verified implementation could produce invalid DEX. The program therefore fails closed instead of emitting a broken artifact or claiming that the OBB will be available automatically.

### Verification

```bash
python -m zipfile -t output/game-standalone.apk
python - <<'PY'
import zipfile
p = 'output/game-standalone.apk'
with zipfile.ZipFile(p) as z:
    print([n for n in z.namelist() if n.startswith('assets/obb/')])
PY
```

Installation validity and signature compatibility must be tested on an authorized device or emulator. An artifact generated with `--no-inject` must not be treated as the final standalone solution.

## Português

### Visão geral

Este repositório contém um programa Python para inspecionar um APK ou pacote XAPK/APKS, localizar um arquivo de expansão Unity (OBB) correspondente e empacotá-lo no APK usando as APIs nativas verificadas do REapk 0.1.1.

O repositório `JRBusiness/REapk`, tag `v0.1.1` (`8dafd5a`), foi inspecionado antes da implementação. A API verificada oferece leitura do manifesto, inspeção de DEX, substituição de corpos de métodos existentes, reconstrução de ZIP alinhado e assinatura nativa de APK. Ela **não oferece uma API suportada para declarar uma nova classe ou método nem para atualizar `class_data` com um método de inicialização**.

Por isso, `build.py` se recusa a produzir por padrão um APK supostamente standalone. O modo explícito `--no-inject` empacota o OBB para testes e inspeção, mas não o extrai automaticamente na inicialização da aplicação.

### Requisitos e configuração

Use Python 3.10 ou mais recente em um ambiente virtual:

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'reapk @ git+https://github.com/JRBusiness/REapk.git@v0.1.1'
```

O script não chama apktool, smali, baksmali, Java, zipalign, apksigner ou keytool.

### Uso

```bash
python build.py input/game.apk
python build.py input/game.xapk
python build.py input/game.apk --obb path/to/main.1435.com.example.game.obb
```

Os comandos acima interrompem deliberadamente a execução com um erro de capacidade antes de produzir um APK. Para testar somente o empacotamento, use a opção explícita:

```bash
python build.py input/game.xapk --no-inject
```

A saída padrão é `output/game-standalone.apk`. Apesar do nome, um artefato produzido com `--no-inject` não é standalone. Ele é assinado com a chave armazenada pelo REapk em `~/.reapk/`; como essa não é a chave original da aplicação, o artefato é destinado a instalação limpa e testes, não à atualização de uma instalação assinada por outra chave.

### Detecção e validação

Para entradas XAPK/APKS/ZIP, o script lê `manifest.json` quando disponível, localiza membros APK e OBB e seleciona o APK base. Pacotes com múltiplos APKs que aparentem ser splits, APKs de arquitetura ou de configuração são rejeitados, pois o REapk 0.1.1 não faz merge de splits.

O manifesto binário é analisado por meio de `apk.manifest.info`. O OBB precisa usar o nome padrão `main.<versionCode>.<package>.obb` ou `patch.<versionCode>.<package>.obb`. O nome é comparado com o pacote e o `versionCode` do APK, e arquivos OBB vazios são rejeitados. Quando existem candidatos main e patch, o candidato main tem preferência.

Quando o empacotamento é habilitado, o OBB é armazenado como `assets/obb/<nome-do-obb>`. A implementação atual não o copia para `/sdcard/Android/obb/<package>/`, pois isso requer um hook DEX de inicialização que o REapk 0.1.1 não consegue declarar com segurança por meio da API verificada.

### Por que a injeção de inicialização não foi implementada

O comportamento completo solicitado exigiria inserir uma chamada em `Application.onCreate()` ou em um método de inicialização de Activity e declarar um helper Dalvik que usasse `AssetManager`, `File`, `mkdirs()` e streams para copiar e verificar o OBB. No REapk 0.1.1, `build_dex()` recebe substituições identificadas por `code_off` de métodos existentes e remapeia pools; `assemble_interned()` monta instruções, mas não cria uma classe nem insere um método em `class_data`. O pacote também não possui um compilador nativo Java/Kotlin para gerar esse helper.

Inventar uma API ou editar `class_data` fora de uma implementação verificada poderia produzir DEX inválido. O programa, portanto, falha de forma segura em vez de gerar um artefato quebrado ou afirmar que o OBB ficará disponível automaticamente.

### Verificação

```bash
python -m zipfile -t output/game-standalone.apk
python - <<'PY'
import zipfile
p = 'output/game-standalone.apk'
with zipfile.ZipFile(p) as z:
    print([n for n in z.namelist() if n.startswith('assets/obb/')])
PY
```

A validade da instalação e a compatibilidade da assinatura devem ser testadas em um dispositivo ou emulador autorizado. Um artefato gerado com `--no-inject` não deve ser tratado como a solução standalone final.

### Autorização e licenciamento

O programa não remove nem contorna LVL, licenciamento do Google Play, DRM, autenticação ou verificações de assinatura. Use-o somente com software para o qual você tenha a autorização necessária.

## Project structure / Estrutura do projeto

```text
reapk-obb-builder/
├── build.py
├── apkobbundler.1
└── README.md
```
