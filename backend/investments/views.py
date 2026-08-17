from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services.transaction_import import (
    TransactionImportError,
    TransactionImporter,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_transactions(request):
    """
    Import transaction data from an Excel or CSV file.

    Expected multipart/form-data field:
        file
    """

    uploaded_file = request.FILES.get("file")

    if uploaded_file is None:
        return Response(
            {
                "success": False,
                "message": (
                    "Please upload an Excel or CSV "
                    "file using the 'file' field."
                ),
            },
            status=400,
        )

    filename = uploaded_file.name.lower()

    if not (
        filename.endswith(".xlsx")
        or filename.endswith(".csv")
    ):
        return Response(
            {
                "success": False,
                "message": (
                    "Only .xlsx and .csv files are supported."
                ),
            },
            status=400,
        )

    try:
        result = TransactionImporter.import_file(
            file=uploaded_file,
            owner=request.user,
        )

    except TransactionImportError as exc:
        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=400,
        )

    except Exception as exc:
        return Response(
            {
                "success": False,
                "message": (
                    "Unexpected error while importing "
                    "the transaction file."
                ),
                "error": str(exc),
            },
            status=500,
        )

    return Response(
        {
            "success": True,
            "message": (
                "Transaction file imported successfully."
            ),
            "data": result,
        },
        status=201,
    )