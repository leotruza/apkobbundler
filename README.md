# REapk OBB Builder
EN:

> **AI Authorship Disclaimer:** This project was created completely by an artificial intelligence agent. Human review, testing, and independent validation are recommended before using it in production or with software for which you do not have authorization.

PT_BR:

> **Disclaimer de autoria por IA:** Este projeto foi criado completamente por um agente de inteligência artificial. Recomenda-se revisão humana, testes e validação independente antes de utilizá-lo em produção ou com software para o qual você não tenha autorização.

## Resultado da inspeção

O repositório `JRBusiness/REapk`, tag `v0.1.1` (`8dafd5a`), foi inspecionado antes da implementação. A API real confirma leitura de manifesto, leitura de DEX, substituição de corpos de métodos, reconstrução ZIP alinhada e assinatura nativa. Ela **não confirma uma API para declarar uma nova classe/método nem para atualizar `class_data` com um novo método de inicialização**.

Por esse motivo, `build.py` implementa de forma real e verificável a detecção APK/XAPK, seleção e validação do OBB, inclusão em `assets/obb/`, reconstrução alinhada e assinatura v2+v3. Por padrão, ele interrompe antes de produzir o APK, pois sem a injeção de startup o artefato não seria standalone. O modo explícito `--no-inject` serve somente para validar a etapa de empacotamento e avisa que o APK não extrai o OBB.

## APIs encontradas

| API | Assinatura real | Uso |
|---|---|---|
| `reapk.Apk` | `Apk.from_bytes(data: bytes, label: str = "<bytes>") -> Apk`; `Apk.open(path: str) -> Apk`; `apk.manifest.info -> dict` | Abrir APK/base APK e obter `package`, `versionCode`, `versionName`, `minSdk` e `targetSdk`. |
| `reapk.DexFile` | `DexFile(data: bytes)`; `classes()`; `class_methods(cdata_off)`; `find_method(class_desc, mname)` | Inspecionar classes e métodos existentes. |
| `reapk.disassemble` | `disassemble(dex, code_off)` | Desmontar o corpo de um método existente. |
| `reapk.assemble` | `assemble(asm, lines)` | Montar linhas smali contra pools existentes. |
| `reapk.assemble_interned` | `assemble_interned(dex, lines) -> (Interner, list[int])` | Montar corpo substituto e internar referências novas. |
| `reapk.build_code_item` | `build_code_item(regs, ins, outs, words) -> bytes` | Criar um `code_item` para um corpo substituto. |
| `reapk.build_dex` | `build_dex(dex, replacements=None, add_strings=None, interner=None) -> bytes` | Reemitir DEX, principalmente trocando corpos de métodos já declarados. |
| `reapk.read_zip_entries` | `read_zip_entries(data: bytes) -> list[dict]` | Ler entradas ZIP preservando payload e metadados. |
| `reapk.stored_entry` | `stored_entry(name: str, data: bytes) -> dict` | Criar entrada armazenada sem compressão. |
| `reapk.write_aligned_zip` | `write_aligned_zip(entries: list[dict]) -> bytes` | Reescrever ZIP; alinha entradas armazenadas (`.so` em 4096, demais em 4). |
| `reapk.apk_sign_v2` | `apk_sign_v2(apk_bytes: bytes) -> bytes` | Inserir assinatura APK v2+v3 nativa; não usa JDK/apksigner. |

O `Interner` administra pools de strings, tipos, protótipos, campos e métodos, mas não adiciona declarações à tabela `class_data`. `DexFile.patch_return()` é apenas um mutador in-place para forçar retorno e não resolve a criação de um hook.

## Ambiente mínimo

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'reapk @ git+https://github.com/JRBusiness/REapk.git@v0.1.1'
```

O script não chama apktool, smali, baksmali, Java, zipalign, apksigner ou keytool.

## Uso

```bash
python build.py input/game.apk
python build.py input/game.xapk
python build.py input/game.apk --obb path/to/main.1435.com.example.game.obb
```

Os comandos acima terminam deliberadamente com erro de capacidade antes de emitir o APK standalone. Para testar apenas a embalagem, de forma explícita:

```bash
python build.py input/game.xapk --no-inject
```

O resultado será `output/game-standalone.apk`, assinado com a chave cacheada pelo REapk em `~/.reapk/`. Como a chave não é a assinatura original da aplicação, o APK é destinado a instalação limpa/teste e não a atualização sobre o pacote original.

## Detecção e validação

Para XAPK/APKS/ZIP, o script lê `manifest.json` quando presente, localiza APKs e OBBs e recusa bundles com múltiplos APKs que indiquem splits/configurações, porque REapk 0.1.1 apenas seleciona a base e não faz merge de splits. O manifesto binário do APK é analisado por `apk.manifest.info`. O OBB aceito precisa seguir exatamente `main.<versionCode>.<package>.obb` ou `patch.<versionCode>.<package>.obb`, e tanto o nome quanto o tamanho não nulo são verificados.

A entrada é adicionada como `assets/obb/<nome-do-obb>`. A implementação ainda não copia esse asset para `/sdcard/Android/obb/<package>/`, pois essa etapa exige o hook DEX que a versão examinada não consegue declarar de maneira suportada.

## Diagnóstico de impossibilidade

A meta completa requer uma alteração semântica no DEX: inserir uma chamada em `Application.onCreate()` ou em um `Activity.onCreate()` e, idealmente, declarar um helper Java/Dalvik com `AssetManager`, `File`, `mkdirs`, streams e lógica de verificação de tamanho. No REapk 0.1.1, `build_dex()` recebe apenas substituições por `code_off` e remapeia pools; `assemble_interned()` monta instruções, mas não cria uma classe nem insere um novo método em `class_data`. Também não há API nativa equivalente a um compilador Java/Kotlin para gerar esse helper.

Inventar uma chamada ou editar bytes de `class_data` fora de uma API confirmada violaria a exigência de produzir DEX válido baseado na implementação real. Portanto, a decisão segura é recusar a saída standalone em vez de produzir um APK quebrado ou alegar que o OBB será disponibilizado automaticamente.

## Verificação da etapa de embalagem

```bash
python -m zipfile -t output/game-standalone.apk
python - <<'PY'
import zipfile
p = 'output/game-standalone.apk'
with zipfile.ZipFile(p) as z:
    print([n for n in z.namelist() if n.startswith('assets/obb/')])
PY
```

A validade de instalação e a compatibilidade de assinatura devem ser verificadas em um dispositivo/emulador autorizado. O artefato gerado com `--no-inject` não deve ser tratado como solução final.

## Estrutura

```text
reapk-obb-builder/
├── build.py
└── README.md
```
