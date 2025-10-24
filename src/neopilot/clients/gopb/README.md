# GitLab Neoai Workflow Service Go Client

This package contains the Protocol Buffer message and service definitions for the Neoai Workflow Service, generated for Go.

## Installation

Add the client to your Go project:

```shell
go get github.com/neopilot-ai/neopilot/clients/gopb
```

## Usage

Import the package in your Go code:

```go
import (
    "github.com/neopilot-ai/neopilot/clients/gopb"
)
```

You can then use the generated protobuf message types and service clients in your application.

## Regenerating the Protocol Buffers

The Go protocol buffer files are generated from the proto definitions using the following command:

```shell
make gen-proto
```

This command should be run from the root of the ai-assist repository.

## License

This client library is licensed under the terms specified in the [LICENSE](./LICENSE) file.
