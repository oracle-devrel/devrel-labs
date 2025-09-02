# download_srt.py
"""
Download a single SRT file from OCI Object Storage.

Usage (conda env with python-oci-sdk installed):
    python download_srt.py --profile aisolutions --outfile test.mp3.srt
"""
import argparse
import oci

NAMESPACE = "axytmnxp84kg"
BUCKET = "SubtitleTranslatorSystem"
OBJECT_NAME = (
    "transcriptions/Test.mp3/"
    "job-amaaaaaaywfcc6aakabq6orrvcofpfoohku2tixcwjoxxlqipiru3u6qptra/"
    "axytmnxp84kg_SubtitleTranslatorSystem_Test.mp3.srt"
)

def main(profile: str, outfile: str) -> None:
    # Load config for the chosen profile
    config = oci.config.from_file(profile_name=profile)
    obj_client = oci.object_storage.ObjectStorageClient(config)

    with open(outfile, "wb") as fp:
        get_resp = obj_client.get_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET,
            object_name=OBJECT_NAME,
        )
        for chunk in get_resp.data.raw.stream(1024 * 1024, decode_content=False):
            fp.write(chunk)

    print(f"Downloaded → {outfile}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="aisolutions",
                        help="OCI CLI profile name (defaults to 'aisolutions')")
    parser.add_argument("--outfile", default="test.mp3.srt",
                        help="Local output filename")
    args = parser.parse_args()
    main(args.profile, args.outfile)
