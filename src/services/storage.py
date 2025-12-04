import os

from src.api.models import Package, PackageMetadata


class LocalStorage:
    def __init__(self):
        print("DEBUG: Initializing LocalStorage (In-Memory)")
        # In-memory storage: {package_id: Package}
        self.packages: dict[str, Package] = {}

    def add_package(self, package: Package) -> None:
        print(f"DEBUG: LocalStorage add_package {package.metadata.ID}")
        self.packages[package.metadata.ID] = package

    def get_package(self, package_id: str) -> Package | None:
        return self.packages.get(package_id)

    def list_packages(self, offset: int = 0, limit: int = 10) -> list[PackageMetadata]:
        print(f"DEBUG: LocalStorage list_packages offset={offset} limit={limit}")
        all_packages = list(self.packages.values())
        # Sort by ID or Name if needed, for now just slice
        # Pagination logic
        return [p.metadata for p in all_packages[offset:offset+limit]]

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
            return [] # Or raise error
        
        matches = []
        for pkg in self.packages.values():
            if pattern.search(pkg.metadata.Name) or pattern.search(pkg.data.Content or ""): # Search in Name or Content
                 matches.append(pkg.metadata)
        return matches

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
        print(f"DEBUG: S3 add_package {package.metadata.ID}")
        # Store metadata
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self._get_key(package.metadata.ID, "metadata"),
            Body=package.metadata.model_dump_json()
        )
        # Store content if exists
        if package.data.Content:
            import base64
            try:
                binary_data = base64.b64decode(package.data.Content)
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=self._get_key(package.metadata.ID, "content"),
                    Body=binary_data
                )
            except Exception as e:
                print(f"DEBUG: S3 add_package content error: {e}")
                pass 
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self._get_key(package.metadata.ID, "full"),
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

    def list_packages(self, offset: int = 0, limit: int = 10) -> list[PackageMetadata]:
        print(f"DEBUG: S3 list_packages offset={offset} limit={limit}")
        paginator = self.s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix, Delimiter='/')
        
        packages = []
        count = 0
        for page in pages:
            # print(f"DEBUG: S3 list page: {page}") # Too verbose?
            for prefix in page.get('CommonPrefixes', []):
                # prefix is packages/{id}/
                pkg_id = prefix.get('Prefix').split('/')[-2]
                # print(f"DEBUG: Found prefix {prefix} -> ID {pkg_id}")
                pkg = self.get_package(pkg_id)
                if pkg:
                    packages.append(pkg.metadata)
                    count += 1
                    if count >= limit + offset:
                        break
            if count >= limit + offset:
                break
        
        print(f"DEBUG: S3 list_packages found {len(packages)} packages")
        return packages[offset:offset+limit]

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
