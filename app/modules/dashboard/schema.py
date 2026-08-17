from pydantic import BaseModel, ConfigDict, Field


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_invoiced_cents: int = Field(
        ...,
        description="Valor total emitido em centavos de todas as faturas geradas.",
        examples=[1281917],
    )
    total_invoices_count: int = Field(
        ...,
        description="Quantidade total de faturas geradas no sistema.",
        examples=[157],
    )
    total_credited_cents: int = Field(
        ...,
        description="Valor total em centavos de faturas com status credited ou paid.",
        examples=[1137828],
    )
    total_credited_count: int = Field(
        ...,
        description="Quantidade de faturas creditadas/pagas.",
        examples=[44],
    )
    total_liquidated_cents: int = Field(
        ...,
        description="Valor líquido total em centavos repassado via Pix com sucesso.",
        examples=[1300987],
    )
    total_liquidated_count: int = Field(
        ...,
        description="Quantidade de transferências Pix concluídas com sucesso.",
        examples=[50],
    )
    conversion_rate_percentage: float = Field(
        ...,
        description="Percentual de conversão de faturas pagas/creditadas sobre o total emitido.",
        examples=[28.03],
    )
