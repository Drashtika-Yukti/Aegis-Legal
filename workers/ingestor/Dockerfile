FROM golang:alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o ingestor main.go

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/ingestor .
EXPOSE 8081
CMD ["./ingestor"]
