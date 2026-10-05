"""Review the actual JobDiva Swagger before supplying this request contract.

No authentication path, parameter spelling, token prefix, or response wrapper
is inferred from an endpoint's display name. Test contracts are synthetic.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

READ_OPERATIONS = frozenset({
    "OpenJobsList", "JobsDetail", "CandidatesProfileDetail",
    "CandidatesLicensesDetail", "CandidatesCertificationsDetails",
    "CandidatesResumesDetail", "ResumesTextDetail",
})


class ContractError(ValueError):
    pass


class AuthContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    method: Literal["GET", "POST"]
    location: Literal["query", "json", "form"]
    client_id_parameter: str
    username_parameter: str
    password_parameter: str
    # Empty means the response itself is the token (JSON string or plain text).
    token_path: tuple[str, ...] = ()
    authorization_prefix: Literal["", "Bearer "]

    @model_validator(mode="after")
    def validate_contract(self):
        if self.path not in {"/api/authenticate", "/apiv2/authenticate", "/apiv2/v2/authenticate"}:
            raise ValueError("Authentication path must be an explicitly reviewed authenticate endpoint")
        keys = (self.client_id_parameter, self.username_parameter, self.password_parameter)
        if len(set(keys)) != 3 or any(not k or not k.isidentifier() for k in keys):
            raise ValueError("Authentication parameter names must be distinct identifiers")
        if self.method == "GET" and self.location != "query":
            raise ValueError("GET authentication requires the reviewed query contract")
        return self


class ReadContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    method: Literal["GET", "POST"]
    location: Literal["query", "json", "form"]
    ids_parameter: str | None = None
    id_encoding: Literal["csv", "repeated", "json"] = "csv"
    id_value_type: Literal["integer", "string"] = "integer"
    parameters: tuple[str, ...] = ()
    required_parameters: tuple[str, ...] = ()
    records_path: tuple[str, ...] = ()
    max_ids: int = Field(default=100, ge=1, le=100)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.path not in {f"/apiv2/bi/{name}" for name in READ_OPERATIONS}:
            raise ValueError("Only the pilot's named V2 reporting reads are allowed")
        is_id_read = not self.path.endswith("/OpenJobsList")
        if is_id_read != bool(self.ids_parameter):
            raise ValueError("Detail reads require an explicit ID parameter; OpenJobsList does not")
        if self.method == "GET" and self.location != "query":
            raise ValueError("GET reads require query parameters")
        if self.id_encoding == "json" and self.location != "json":
            raise ValueError("JSON ID arrays require a JSON body")
        if self.id_encoding == "repeated" and self.location == "json":
            raise ValueError("Repeated IDs require a query or form contract")
        if not set(self.required_parameters).issubset(self.parameters):
            raise ValueError("Required parameters must be declared")
        if self.ids_parameter is not None and self.ids_parameter in self.parameters:
            raise ValueError("IDs cannot also be supplied through arbitrary parameters")
        if any(not k.isidentifier() for k in (*self.parameters, *( (self.ids_parameter,) if self.ids_parameter else () ))):
            raise ValueError("Parameter names must be identifiers")
        return self


class JobDivaContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    purpose: Literal["pilot", "test"] = "pilot"
    reviewed: bool = False
    evidence: str = ""
    authentication: AuthContract
    operations: dict[str, ReadContract]

    @model_validator(mode="after")
    def validate_operations(self):
        for name, operation in self.operations.items():
            if name not in READ_OPERATIONS or operation.path.rsplit("/", 1)[-1] != name:
                raise ValueError("Operation name and approved read endpoint must match")
        if self.reviewed and not self.evidence.strip():
            raise ValueError("Record the official schema version and review evidence")
        return self
