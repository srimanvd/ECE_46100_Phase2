import os

from src.api.models import Package, PackageMetadata, PackageQuery


class LocalStorage:
    def __init__(self):
        print("DEBUG: Initializing LocalStorage (In-Memory)")
        # In-memory storage: {package_id: Package}
        self.packages: dict[str, Package] = {}

    def add_package(self, package: Package) -> None:
        print(f"DEBUG: LocalStorage add_package {package.metadata.id}")
        self.packages[package.metadata.id] = package

    def get_package(self, package_id: str) -> Package | None:
        return self.packages.get(package_id)

    def list_packages(self, queries: list[PackageQuery] | None = None, offset: int = 0, limit: int = 10) -> list[PackageMetadata]:
        print(f"DEBUG: LocalStorage list_packages queries={queries} offset={offset} limit={limit}")
        all_packages = list(self.packages.values())
        
        # Filter
        if not queries:
             filtered = all_packages
        else:
            filtered = []
            for pkg in all_packages:
                match = False
                for q in queries:
                    # Name match (exact or wildcard)
                    if q.name != "*" and q.name != pkg.metadata.name:
                        continue
                    
                    # Version match (exact for now)
                    if q.version and q.version != pkg.metadata.version:
                        continue
                        
                    # Type match
                    # q.types is list[str] e.g. ["code", "model"]
                    # pkg.metadata.type is str e.g. "code"
                    if q.types and pkg.metadata.type not in [t.lower() for t in q.types]:
                        continue
                        
                    match = True
                    break
                if match:
                    filtered.append(pkg)
        
        # Pagination logic
        return [p.metadata for p in filtered[offset:offset+limit]]

    def delete_package(self, package_id: str) -> bool:
        print(f"DEBUG: LocalStorage delete_package {package_id}")
        if package_id in self.packages:
            del self.packages[package_id]
            return True
        return False

    def reset(self) -> None:
        print("DEBUG: LocalStorage reset called")
        self.packages.clear()

    def search_by_regex(self, regex: str) -> list[PackageMetadata]:
        import re
        try:
            pattern = re.compile(regex)
        except re.error:
            return []
        
        matches = []
        for pkg in self.packages.values():
            # Search in name and readme
            if pattern.search(pkg.metadata.name) or pattern.search(pkg.data.readme or ""):
                matches.append(pkg.metadata)
        return matches

    def get_download_url(self, id: str) -> str | None:
        return None

class S3Storage:
    def __init__(self, bucket_name: str, region: str):

        import boto3
        self.bucket = bucket_name
        self.s3 = boto3.client('s3', region_name=region)
        self.prefix = "packages/"

    def _get_key(self, package_id: str, kind: str = "metadata") -> str:
        # kind: metadata | content
        ext = "json" if kind == "metadata" else "zip"
        return f"{self.prefix}{package_id}/{kind}.{ext}"

    def add_package(self, package: Package) -> None:
        print(f"DEBUG: S3 add_package {package.metadata.id}")
        # Store metadata
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self._get_key(package.metadata.id, "metadata"),
            Body=package.metadata.model_dump_json()
        )
        # Store content if exists
        if package.data.content:
            import base64
            try:
                binary_data = base64.b64decode(package.data.content)
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=self._get_key(package.metadata.id, "content"),
                    Body=binary_data
                )
                # Also store with package_id.zip name for direct download
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=f"{self.prefix}{package.metadata.id}/{package.metadata.id}.zip",
                    Body=binary_data
                )
            except Exception as e:
                print(f"DEBUG: S3 add_package content error: {e}")
                pass 
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self._get_key(package.metadata.id, "full"),
            Body=package.model_dump_json()
        )

    def get_package(self, package_id: str) -> Package | None:
        from botocore.exceptions import ClientError
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=self._get_key(package_id, "full"))
            content = response['Body'].read().decode('utf-8')
            return Package.model_validate_json(content)
        except ClientError:
            return None

    def list_packages(self, queries: list[PackageQuery] | None = None, offset: int = 0, limit: int = 10) -> list[PackageMetadata]:
        print(f"DEBUG: S3 list_packages queries={queries} offset={offset} limit={limit}")
        paginator = self.s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix, Delimiter='/')
        
        # In S3, we can't easily filter without reading metadata. 
        # For this scale, we list all and filter in memory (inefficient but works for small scale).
        # A better way would be using S3 Select or storing metadata in DynamoDB.
        
        packages = []
        # We need to scan until we find (offset + limit) matches
        
        count = 0
        skipped = 0
        
        for page in pages:
            for prefix in page.get('CommonPrefixes', []):
                pkg_id = prefix.get('Prefix').split('/')[-2]
                pkg = self.get_package(pkg_id)
                if not pkg:
                    continue
                
                # Apply Filter
                match = False
                if not queries:
                    match = True
                else:
                    for q in queries:
                        if q.name != "*" and q.name != pkg.metadata.name:
                            continue
                        if q.version and q.version != pkg.metadata.version:
                            continue
                        if q.types and pkg.metadata.type not in [t.lower() for t in q.types]:
                            continue
                        match = True
                        break
                
                if match:
                    if skipped < offset:
                        skipped += 1
                        continue
                    
                    packages.append(pkg.metadata)
                    count += 1
                    if count >= limit:
                        break
            if count >= limit:
                break
        
        print(f"DEBUG: S3 list_packages found {len(packages)} packages")
        return packages

    def delete_package(self, package_id: str) -> bool:
        print(f"DEBUG: S3 delete_package {package_id}")
        objects = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=f"{self.prefix}{package_id}/")
        if 'Contents' in objects:
            delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
            self.s3.delete_objects(Bucket=self.bucket, Delete={'Objects': delete_keys})
            return True
        return False

    def reset(self) -> None:
        print("DEBUG: S3 reset called")
        # Delete everything in bucket under prefix
        objects = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix)
        if 'Contents' in objects:
            delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
            print(f"DEBUG: S3 reset deleting {len(delete_keys)} objects")
            self.s3.delete_objects(Bucket=self.bucket, Delete={'Objects': delete_keys})
        else:
            print("DEBUG: S3 reset found no objects to delete")

    def search_by_regex(self, regex: str) -> list[PackageMetadata]:
        return []




def get_storage():
    storage_type = os.environ.get("STORAGE_TYPE", "LOCAL").upper()
    print(f"DEBUG: Initializing storage. Type: {storage_type}")
    if storage_type == "S3":
        bucket = os.environ.get("BUCKET_NAME", "ece46100-registry")
        region = os.environ.get("AWS_REGION", "us-east-1")
        print(f"DEBUG: S3 Bucket: {bucket}, Region: {region}")
        return S3Storage(bucket, region)
    return LocalStorage()

# Global instance
storage = get_storage()
