from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Union

# --- Package Models ---

class PackageMetadata(BaseModel):
    Name: str = Field(..., description="Package name")
    Version: str = Field(..., description="Package version")
    ID: str = Field(..., description="Package ID")

class PackageData(BaseModel):
    Content: Optional[str] = Field(None, description="Base64 encoded zip file content")
    URL: Optional[str] = Field(None, description="Package URL (for ingest)")
    JSProgram: Optional[str] = Field(None, description="JavaScript program for sensitive modules")

class Package(BaseModel):
    metadata: PackageMetadata
    data: PackageData

class PackageRating(BaseModel):
    BusFactor: float
    BusFactorLatency: float
    Correctness: float
    CorrectnessLatency: float
    RampUp: float
    RampUpLatency: float
    ResponsiveMaintainer: float
    ResponsiveMaintainerLatency: float
    LicenseScore: float
    LicenseScoreLatency: float
    GoodPinningPractice: float
    GoodPinningPracticeLatency: float
    PullRequest: float
    PullRequestLatency: float
    NetScore: float
    NetScoreLatency: float
    TreeScore: float
    TreeScoreLatency: float
    Reproducibility: float
    ReproducibilityLatency: float

class PackageHistoryEntry(BaseModel):
    User: dict
    Date: str
    PackageMetadata: PackageMetadata
    Action: str

class PackageQuery(BaseModel):
    Name: str = Field(..., description="Package name")
    Version: Optional[str] = Field(None, description="Package version")

class PackageRegEx(BaseModel):
    RegEx: str = Field(..., description="Regex for searching packages")

# --- User/Auth Models ---

class User(BaseModel):
    name: str
    isAdmin: bool

class AuthenticationRequest(BaseModel):
    User: User
    Secret: str

class AuthenticationToken(BaseModel):
    bearerToken: str

# --- Error Models ---

class Error(BaseModel):
    code: int
    message: str
