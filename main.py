import uvicorn


def main() -> None:
    uvicorn.run(
        "payment_gateway_api.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
