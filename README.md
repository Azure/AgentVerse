# AgentVerse

## Introduction

AgentVerse is a curated collection of agentic use cases developed within Microsoft and packaged for direct execution and deployment in your own Azure subscription. Each scenario demonstrates how autonomous, AI-driven agents can be applied to solve real-world problems, providing ready-to-run reference implementations that you can explore, adapt, and operationalize in your own environment.

This initiative is the result of collaboration across multiple Microsoft teams, bringing together diverse expertise to showcase the breadth of agentic patterns and best practices. The goal is to offer a practical, production-oriented starting point that accelerates the adoption of agentic solutions while remaining flexible enough to fit your specific needs.

## Unified portal & global deploy

Every demo under [`src/`](src/) is fully independent, but they can also be shown
and deployed **together**:

- **Portal** — a catalog-driven web app ([`portal/`](portal/)) with **one tab
  per demo**, embedding each demo's frontend. Hosted as an Azure Container App.
- **Global deploy** — one Terraform configuration ([`infra/`](infra/), outside
  `src/`) that provisions a shared platform, deploys all enabled demos, and
  optionally registers their agents. It leans on each demo's own Terraform/Bicep.
- **Catalog** — each demo ships an `agentverse.yaml`; `catalog.json` is generated
  from them and drives the portal (see [`src/templates/catalog/`](src/templates/catalog/)).

New use case? Follow the onboarding memory in
[`docs/adding-a-demo.md`](docs/adding-a-demo.md) — add two files (a manifest and
a deployment entry) and the demo appears as a new tab.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
