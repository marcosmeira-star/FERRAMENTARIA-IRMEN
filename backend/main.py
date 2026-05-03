from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "ferramentaria.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    ativo: bool = True


class Ferramenta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    quantidade_total: int
    quantidade_disponivel: int
    ativo: bool = True


class Emprestimo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    ferramenta_id: int = Field(foreign_key="ferramenta.id")
    quantidade: int
    quantidade_devolvida: int = 0
    aberto: bool = True
    criado_em: datetime = Field(default_factory=datetime.utcnow)


class Movimentacao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str
    cliente_id: int = Field(foreign_key="cliente.id")
    ferramenta_id: int = Field(foreign_key="ferramenta.id")
    quantidade: int
    observacao: str = ""
    criado_em: datetime = Field(default_factory=datetime.utcnow)


class ClienteIn(BaseModel):
    nome: str


class FerramentaIn(BaseModel):
    nome: str
    quantidade_total: int


class EmprestimoIn(BaseModel):
    cliente_id: int
    ferramenta_id: int
    quantidade: int
    observacao: str = ""


class DevolucaoIn(BaseModel):
    emprestimo_id: int
    quantidade: int
    observacao: str = ""


app = FastAPI(title="Ferramentaria Irmen API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    SQLModel.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard")
def dashboard():
    with Session(engine) as session:
        total_clientes = len(session.exec(select(Cliente).where(Cliente.ativo.is_(True))).all())
        ferramentas = session.exec(select(Ferramenta).where(Ferramenta.ativo.is_(True))).all()
        total_disponivel = sum(f.quantidade_disponivel for f in ferramentas)
        total_emprestado = sum(max(0, f.quantidade_total - f.quantidade_disponivel) for f in ferramentas)
        movs = session.exec(select(Movimentacao).order_by(Movimentacao.criado_em.desc())).all()[:10]
        return {
            "total_clientes": total_clientes,
            "total_disponivel": total_disponivel,
            "total_emprestado": total_emprestado,
            "ultimas_movimentacoes": movs,
        }


@app.get("/clientes")
def listar_clientes(q: str = ""):
    with Session(engine) as session:
        query = select(Cliente)
        if q:
            query = query.where(Cliente.nome.contains(q))
        return session.exec(query.order_by(Cliente.nome)).all()


@app.post("/clientes")
def criar_cliente(data: ClienteIn):
    with Session(engine) as session:
        c = Cliente(nome=data.nome)
        session.add(c)
        session.commit()
        session.refresh(c)
        return c


@app.patch("/clientes/{cliente_id}/toggle")
def toggle_cliente(cliente_id: int):
    with Session(engine) as session:
        c = session.get(Cliente, cliente_id)
        if not c:
            raise HTTPException(404, "Cliente não encontrado")
        c.ativo = not c.ativo
        session.add(c)
        session.commit()
        return c


@app.get("/ferramentas")
def listar_ferramentas(q: str = ""):
    with Session(engine) as session:
        query = select(Ferramenta)
        if q:
            query = query.where(Ferramenta.nome.contains(q))
        return session.exec(query.order_by(Ferramenta.nome)).all()


@app.post("/ferramentas")
def criar_ferramenta(data: FerramentaIn):
    if data.quantidade_total < 0:
        raise HTTPException(400, "Quantidade inválida")
    with Session(engine) as session:
        f = Ferramenta(nome=data.nome, quantidade_total=data.quantidade_total, quantidade_disponivel=data.quantidade_total)
        session.add(f)
        session.commit()
        session.refresh(f)
        return f


@app.patch("/ferramentas/{ferramenta_id}/toggle")
def toggle_ferramenta(ferramenta_id: int):
    with Session(engine) as session:
        f = session.get(Ferramenta, ferramenta_id)
        if not f:
            raise HTTPException(404, "Ferramenta não encontrada")
        f.ativo = not f.ativo
        session.add(f)
        session.commit()
        return f


@app.post("/emprestimos")
def emprestar(data: EmprestimoIn):
    if data.quantidade <= 0:
        raise HTTPException(400, "Quantidade deve ser maior que zero")
    with Session(engine) as session:
        cliente = session.get(Cliente, data.cliente_id)
        ferramenta = session.get(Ferramenta, data.ferramenta_id)
        if not cliente or not cliente.ativo:
            raise HTTPException(400, "Cliente inválido/inativo")
        if not ferramenta or not ferramenta.ativo:
            raise HTTPException(400, "Ferramenta inválida/inativa")
        if ferramenta.quantidade_disponivel < data.quantidade:
            raise HTTPException(400, "Saldo insuficiente")
        ferramenta.quantidade_disponivel -= data.quantidade
        emp = Emprestimo(cliente_id=cliente.id, ferramenta_id=ferramenta.id, quantidade=data.quantidade)
        mov = Movimentacao(tipo="emprestimo", cliente_id=cliente.id, ferramenta_id=ferramenta.id, quantidade=data.quantidade, observacao=data.observacao)
        session.add(ferramenta)
        session.add(emp)
        session.add(mov)
        session.commit()
        return {"ok": True}


@app.get("/emprestimos/abertos")
def abertos():
    with Session(engine) as session:
        emps = session.exec(select(Emprestimo).where(Emprestimo.aberto.is_(True)).order_by(Emprestimo.criado_em.desc())).all()
        return emps


@app.post("/devolucoes")
def devolver(data: DevolucaoIn):
    if data.quantidade <= 0:
        raise HTTPException(400, "Quantidade deve ser maior que zero")
    with Session(engine) as session:
        emp = session.get(Emprestimo, data.emprestimo_id)
        if not emp:
            raise HTTPException(404, "Empréstimo não encontrado")
        pendente = emp.quantidade - emp.quantidade_devolvida
        if data.quantidade > pendente:
            raise HTTPException(400, "Devolução maior que o pendente")
        ferramenta = session.get(Ferramenta, emp.ferramenta_id)
        emp.quantidade_devolvida += data.quantidade
        emp.aberto = emp.quantidade_devolvida < emp.quantidade
        ferramenta.quantidade_disponivel += data.quantidade
        mov = Movimentacao(tipo="devolucao", cliente_id=emp.cliente_id, ferramenta_id=emp.ferramenta_id, quantidade=data.quantidade, observacao=data.observacao)
        session.add(emp)
        session.add(ferramenta)
        session.add(mov)
        session.commit()
        return {"ok": True}


@app.get("/historico")
def historico():
    with Session(engine) as session:
        return session.exec(select(Movimentacao).order_by(Movimentacao.criado_em.desc())).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8765)

