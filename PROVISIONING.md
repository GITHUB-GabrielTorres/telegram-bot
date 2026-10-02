# Provisioning

Passos manuais necessários para preparar o ambiente do bot.

## Firestore

### Índice composto em `movements`

Criado manualmente pelo console do Firestore:

| Coleção     | Campos                                   | Escopo     |
|-------------|------------------------------------------|------------|
| `movements` | `person` (Ascending), `amount` (Ascending) | Collection |

**Por que manual:** a Service Account usada pelo projeto não tem permissão para gerenciar índices do Firestore (ex.: papel `roles/datastore.indexAdmin`), então o índice não pode ser criado pela aplicação/CLI com essa credencial. Ele foi criado direto no console com uma conta que tem essa permissão.

Se o ambiente for recriado (novo projeto/banco), esse índice precisa ser criado de novo da mesma forma — ou conceder à SA a permissão de gerenciar índices.
