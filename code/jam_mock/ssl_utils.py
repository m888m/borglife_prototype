"""
SSL/TLS utilities for Kusama RPC connections.

Provides SSL context configuration and testing utilities for LibreSSL compatibility.
"""

import ssl
import asyncio
from typing import Dict, Any, Optional, List
import socket
import time


class SSLUtils:
    """
    SSL/TLS utilities for Kusama RPC connections with LibreSSL compatibility.
    """

    @staticmethod
    def create_libressl_compatible_context() -> ssl.SSLContext:
        """
        Create SSL context compatible with LibreSSL 2.8.3.

        LibreSSL 2.8.3 doesn't support TLS 1.3, so we configure for TLS 1.2 max.

        Returns:
            Configured SSL context
        """
        context = ssl.create_default_context()

        # Disable TLS 1.3 if available (though LibreSSL doesn't have it)
        if hasattr(ssl, 'PROTOCOL_TLSv1_3'):
            # If we had TLS 1.3, we'd disable it here for compatibility
            pass

        # Set maximum TLS version to 1.2 for LibreSSL compatibility
        if hasattr(context, 'maximum_version'):
            context.maximum_version = ssl.TLSVersion.TLSv1_2

        # Set minimum TLS version to 1.1 for broader compatibility
        if hasattr(context, 'minimum_version'):
            context.minimum_version = ssl.TLSVersion.TLSv1_1

        # Enable certificate verification
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Add common cipher suites that work with LibreSSL
        context.set_ciphers(
            'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:'
            'ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:'
            'AES128-GCM-SHA256:AES256-GCM-SHA384'
        )

        return context

    @staticmethod
    def get_ssl_info() -> Dict[str, Any]:
        """
        Get SSL library information.

        Returns:
            Dictionary with SSL library details
        """
        return {
            'openssl_version': ssl.OPENSSL_VERSION,
            'has_tls_1_3': hasattr(ssl, 'PROTOCOL_TLSv1_3'),
            'available_protocols': [p for p in dir(ssl) if p.startswith('PROTOCOL_TLS')],
            'has_tls_versions': hasattr(ssl, 'TLSVersion'),
            'tls_versions': [v for v in dir(ssl) if v.startswith('TLSv')] if hasattr(ssl, 'TLSVersion') else []
        }

    @staticmethod
    async def test_ssl_connection(host: str, port: int = 443, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Test SSL connection to a host.

        Args:
            host: Hostname to test
            port: Port number (default 443)
            timeout: Connection timeout in seconds

        Returns:
            Test results dictionary
        """
        result = {
            'host': host,
            'port': port,
            'success': False,
            'error': None,
            'ssl_info': None,
            'response_time': None
        }

        start_time = time.time()

        try:
            # Create socket and wrap with SSL
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # Connect
            sock.connect((host, port))

            # Wrap with SSL
            context = SSLUtils.create_libressl_compatible_context()
            ssl_sock = context.wrap_socket(sock, server_hostname=host)

            # Perform handshake
            ssl_sock.do_handshake()

            # Get SSL info
            cert = ssl_sock.getpeercert()
            cipher = ssl_sock.cipher()

            result.update({
                'success': True,
                'ssl_info': {
                    'version': ssl_sock.version(),
                    'cipher': cipher,
                    'certificate_subject': cert.get('subject') if cert else None,
                    'certificate_issuer': cert.get('issuer') if cert else None,
                    'certificate_expires': cert.get('notAfter') if cert else None
                },
                'response_time': time.time() - start_time
            })

            ssl_sock.close()

        except Exception as e:
            result.update({
                'error': str(e),
                'response_time': time.time() - start_time
            })

        return result

    @staticmethod
    async def test_multiple_tls_versions(host: str, port: int = 443) -> Dict[str, Any]:
        """
        Test connection with different TLS versions.

        Args:
            host: Hostname to test
            port: Port number

        Returns:
            Test results for each TLS version
        """
        results = {}

        # Test TLS versions available in LibreSSL
        tls_versions = [
            ('TLSv1.2', ssl.PROTOCOL_TLSv1_2),
            ('TLSv1.1', ssl.PROTOCOL_TLSv1_1),
        ]

        # Add TLS 1.3 if available
        if hasattr(ssl, 'PROTOCOL_TLSv1_3'):
            tls_versions.insert(0, ('TLSv1.3', ssl.PROTOCOL_TLSv1_3))

        for version_name, protocol in tls_versions:
            try:
                context = ssl.SSLContext(protocol)
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((host, port))

                ssl_sock = context.wrap_socket(sock, server_hostname=host)
                ssl_sock.do_handshake()

                results[version_name] = {
                    'success': True,
                    'version': ssl_sock.version(),
                    'cipher': ssl_sock.cipher()
                }

                ssl_sock.close()

            except Exception as e:
                results[version_name] = {
                    'success': False,
                    'error': str(e)
                }

        return results

    @staticmethod
    def validate_ssl_config(context: ssl.SSLContext) -> Dict[str, Any]:
        """
        Validate SSL context configuration.

        Args:
            context: SSL context to validate

        Returns:
            Validation results
        """
        validation = {
            'has_check_hostname': getattr(context, 'check_hostname', None),
            'verify_mode': getattr(context, 'verify_mode', None),
            'protocol': getattr(context, 'protocol', None),
            'options': getattr(context, 'options', None),
            'minimum_version': getattr(context, 'minimum_version', None),
            'maximum_version': getattr(context, 'maximum_version', None),
            'ciphers': None
        }

        # Try to get cipher list
        try:
            validation['ciphers'] = context.get_ciphers()
        except Exception:
            pass

        return validation


async def test_kusama_endpoints() -> Dict[str, Any]:
    """
    Test SSL connections to Kusama RPC endpoints.

    Returns:
        Test results for all endpoints
    """
    endpoints = [
        ('kusama-rpc.polkadot.io', 443),
        ('kusama.api.onfinality.io', 443),
        ('kusama-rpc.dwellir.com', 443),
    ]

    results = {}

    for host, port in endpoints:
        print(f"Testing SSL connection to {host}:{port}...")
        result = await SSLUtils.test_ssl_connection(host, port, timeout=10.0)
        results[host] = result

        if result['success']:
            print(f"✅ {host}: {result['ssl_info']['version']} - {result['ssl_info']['cipher'][0]}")
        else:
            print(f"❌ {host}: {result['error']}")

    return results


if __name__ == "__main__":
    # Run SSL tests when executed directly
    asyncio.run(test_kusama_endpoints())