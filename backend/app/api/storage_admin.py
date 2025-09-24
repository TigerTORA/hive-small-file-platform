from __future__ import annotations

import shlex
import subprocess
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import SessionLocal, get_db
from app.models.cluster import Cluster
from app.services.scan_service import scan_task_manager
from app.utils.webhdfs_client import WebHDFSClient

router = APIRouter()


class SSHBase(BaseModel):
    ssh_host: str
    ssh_user: str = "hdfs"
    ssh_port: int = 22
    ssh_key_path: Optional[str] = None
    kinit_principal: Optional[str] = None
    kinit_keytab: Optional[str] = None
    dry_run: bool = False


class ECSetPolicyRequest(SSHBase):
    path: str
    policy: str = Field(..., description="EC策略名，如 RS-6-3-1024k")
    recursive: bool = True


class RunMoverRequest(SSHBase):
    path: str


class SetReplicationRequest(BaseModel):
    path: str
    replication: int = Field(..., ge=1, le=10, description="目标副本数，1-10 之间")
    recursive: bool = Field(
        default=False, description="是否递归设置子目录/文件的副本数"
    )
    dry_run: bool = False


def _ssh_cmd(payload: SSHBase, remote: str) -> List[str]:
    cmd = ["ssh"]
    if payload.ssh_key_path:
        cmd += ["-i", payload.ssh_key_path]
    cmd += [
        "-p",
        str(payload.ssh_port),
        f"{payload.ssh_user}@{payload.ssh_host}",
        "--",
        remote,
    ]
    return cmd


def _with_kinit(payload: SSHBase, remote: str) -> str:
    if payload.kinit_principal and payload.kinit_keytab:
        return f"kinit -kt {shlex.quote(payload.kinit_keytab)} {shlex.quote(payload.kinit_principal)} && {remote}"
    return remote


@router.post("/ec/set-policy/{cluster_id}")
async def set_ec_policy(
    cluster_id: int, req: ECSetPolicyRequest, db: Session = Depends(get_db)
):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    task = scan_task_manager.create_scan_task(
        db,
        cluster_id=cluster_id,
        task_type="ec-set-policy",
        task_name=f"EC策略: {req.policy}",
        target_database=None,
        target_table=None,
    )
    task_id = task.task_id

    def run():
        db_thread = SessionLocal()
        try:
            scan_task_manager.safe_update_progress(
                db_thread,
                task_id,
                status="running",
                total_items=2,
                completed_items=0,
                current_item="init",
            )
            scan_task_manager.info(
                task_id,
                "EC101",
                "开始设置EC策略",
                db=db_thread,
                phase="ec",
                ctx={
                    "policy": req.policy,
                    "path": req.path,
                    "recursive": req.recursive,
                },
            )
            # 基础命令：对根路径设置策略
            base = f"hdfs ec -setPolicy -path {shlex.quote(req.path)} -policy {shlex.quote(req.policy)}"
            remote_cmd = _with_kinit(req, base)
            cmd = _ssh_cmd(req, remote_cmd)
            scan_task_manager.safe_update_progress(
                db_thread, task_id, completed_items=1, current_item="exec"
            )
            scan_task_manager.info(
                task_id,
                "EC120",
                "执行命令",
                db=db_thread,
                phase="ec",
                ctx={
                    "ssh": f"{req.ssh_user}@{req.ssh_host}:{req.ssh_port}",
                    "dry_run": req.dry_run,
                },
            )
            if req.dry_run:
                scan_task_manager.info(
                    task_id,
                    "EC121",
                    "命令预览",
                    db=db_thread,
                    phase="ec",
                    ctx={"cmd": " ".join(cmd)},
                )
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=2, current_item="done"
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
                return
            try:
                code = subprocess.call(cmd)
            except Exception as e:
                scan_task_manager.error(
                    task_id, "EEC190", f"SSH执行失败: {e}", db=db_thread, phase="ec"
                )
                code = -1
            if code == 0:
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=2, current_item="done"
                )
                scan_task_manager.info(
                    task_id, "EC190", "EC策略设置完成", db=db_thread, phase="ec"
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
            else:
                scan_task_manager.complete_task(
                    db_thread, task_id, success=False, error_message=f"exit={code}"
                )
        finally:
            try:
                db_thread.close()
            except Exception:
                pass

    import threading

    threading.Thread(target=run, daemon=True).start()
    return {"message": "EC set started", "task_id": task_id, "cluster_id": cluster_id}


@router.post("/storage/mover/{cluster_id}")
async def run_mover(
    cluster_id: int, req: RunMoverRequest, db: Session = Depends(get_db)
):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    task = scan_task_manager.create_scan_task(
        db,
        cluster_id=cluster_id,
        task_type="storage-mover",
        task_name=f"Mover: {req.path}",
        target_database=None,
        target_table=None,
    )
    task_id = task.task_id

    def run():
        db_thread = SessionLocal()
        try:
            scan_task_manager.safe_update_progress(
                db_thread,
                task_id,
                status="running",
                total_items=1,
                completed_items=0,
                current_item="exec",
            )
            scan_task_manager.info(
                task_id,
                "MV101",
                "开始执行 mover",
                db=db_thread,
                phase="mover",
                ctx={"path": req.path},
            )
            base = f"hdfs mover -p {shlex.quote(req.path)}"
            remote_cmd = _with_kinit(req, base)
            cmd = _ssh_cmd(req, remote_cmd)
            if req.dry_run:
                scan_task_manager.info(
                    task_id,
                    "MV121",
                    "命令预览",
                    db=db_thread,
                    phase="mover",
                    ctx={"cmd": " ".join(cmd)},
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
                return
            try:
                code = subprocess.call(cmd)
            except Exception as e:
                scan_task_manager.error(
                    task_id, "EMV190", f"SSH执行失败: {e}", db=db_thread, phase="mover"
                )
                code = -1
            if code == 0:
                scan_task_manager.info(
                    task_id, "MV190", "mover 执行完成", db=db_thread, phase="mover"
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
            else:
                scan_task_manager.complete_task(
                    db_thread, task_id, success=False, error_message=f"exit={code}"
                )
        finally:
            try:
                db_thread.close()
            except Exception:
                pass

    import threading

    threading.Thread(target=run, daemon=True).start()
    return {"message": "Mover started", "task_id": task_id, "cluster_id": cluster_id}


@router.post("/storage/set-replication/{cluster_id}")
async def set_replication(
    cluster_id: int, req: SetReplicationRequest, db: Session = Depends(get_db)
):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    task = scan_task_manager.create_scan_task(
        db,
        cluster_id=cluster_id,
        task_type="storage-set-replication",
        task_name=f"SetRep: {req.replication}",
        target_database=None,
        target_table=None,
    )
    task_id = task.task_id

    def run():
        db_thread = SessionLocal()
        try:
            scan_task_manager.safe_update_progress(
                db_thread,
                task_id,
                status="running",
                total_items=2,
                completed_items=0,
                current_item="prepare",
            )
            scan_task_manager.info(
                task_id,
                "SR101",
                "开始设置副本数",
                db=db_thread,
                phase="replication",
                ctx={
                    "replication": req.replication,
                    "path": req.path,
                    "recursive": req.recursive,
                    "dry_run": req.dry_run,
                },
            )

            client = WebHDFSClient(
                cluster.hdfs_namenode_url,
                cluster.hdfs_user or "hdfs",
            )

            scan_task_manager.safe_update_progress(
                db_thread, task_id, completed_items=1, current_item="execute"
            )

            if req.dry_run:
                scan_task_manager.info(
                    task_id,
                    "SR121",
                    "Dry run: 未实际调用 WebHDFS",
                    db=db_thread,
                    phase="replication",
                )
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=2, current_item="done"
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
                return

            ok, msg = client.set_replication(
                req.path, req.replication, recursive=req.recursive
            )

            if ok:
                scan_task_manager.safe_update_progress(
                    db_thread, task_id, completed_items=2, current_item="done"
                )
                scan_task_manager.info(
                    task_id,
                    "SR199",
                    "副本数设置完成",
                    db=db_thread,
                    phase="replication",
                    ctx={"message": msg},
                )
                scan_task_manager.complete_task(db_thread, task_id, success=True)
            else:
                scan_task_manager.error(
                    task_id,
                    "SR190",
                    f"设置副本数失败: {msg}",
                    db=db_thread,
                    phase="replication",
                )
                scan_task_manager.complete_task(
                    db_thread,
                    task_id,
                    success=False,
                    error_message=msg,
                )
        except Exception as exc:
            scan_task_manager.error(
                task_id,
                "SR198",
                f"执行异常: {exc}",
                db=db_thread,
                phase="replication",
            )
            scan_task_manager.complete_task(
                db_thread, task_id, success=False, error_message=str(exc)
            )
        finally:
            try:
                db_thread.close()
            except Exception:
                pass

    import threading

    threading.Thread(target=run, daemon=True).start()
    return {
        "message": "Set replication started",
        "task_id": task_id,
        "cluster_id": cluster_id,
    }
