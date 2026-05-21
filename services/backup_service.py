import io
import zipfile


def dataframe_zip(exports):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in exports.items():
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer.getvalue()
