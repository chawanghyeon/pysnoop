# utils/gen_cert.py
from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_self_signed_cert(cert_path, key_path, hostname="localhost"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )

    cert_dir = Path(cert_path).parent
    cert_dir.mkdir(parents=True, exist_ok=True)

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )

    print(f"✅ Self-signed cert generated at {cert_path}")


if __name__ == "__main__":
    # 예시 실행: 스크립트를 직접 실행할 때만 인증서 생성
    # 기본 경로는 스크립트가 위치한 디렉토리 기준으로 ssl/ 폴더를 가정
    script_dir = Path(__file__).resolve().parent
    default_cert_path = script_dir.parent / "ssl" / "cert.pem"  # server/ssl/cert.pem
    default_key_path = script_dir.parent / "ssl" / "key.pem"  # server/ssl/key.pem

    # 디렉토리 생성 보장
    default_cert_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating self-signed certificate at: {default_cert_path}")
    print(f"Generating private key at: {default_key_path}")
    generate_self_signed_cert(str(default_cert_path), str(default_key_path), hostname="localhost")
    print("To use a different hostname, run: python gen_cert.py <hostname>")
    # python gen_cert.py my.server.com 와 같이 실행하여 hostname 변경 가능
    import sys

    if len(sys.argv) > 1:
        custom_hostname = sys.argv[1]
        print(f"\nGenerating self-signed certificate for custom hostname: {custom_hostname}")
        generate_self_signed_cert(
            str(default_cert_path), str(default_key_path), hostname=custom_hostname
        )
