#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import datetime as dt
import os
import sys
import time
from pathlib import Path
from subprocess import Popen

try:
    import psutil
except ImportError:
    print("缺少依赖: psutil，请先执行 `pip install psutil` 后再运行。")
    sys.exit(1)


def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{now_str()}] {message}")


def status_text(proc: psutil.Process) -> str:
    try:
        st = proc.status()
    except psutil.Error:
        return "未知"
    if st in (psutil.STATUS_RUNNING,):
        return "运行中"
    if st in (psutil.STATUS_SLEEPING, psutil.STATUS_WAKING):
        return "休眠中"
    if st in (psutil.STATUS_STOPPED, psutil.STATUS_TRACING_STOP):
        return "已停止"
    if st in (psutil.STATUS_ZOMBIE,):
        return "僵尸"
    if st in (psutil.STATUS_DEAD,):
        return "已结束"
    return "运行中"


def ensure_target(target: Path) -> None:
    if not target.exists():
        print(f"未找到目标程序: {target}")
        sys.exit(1)


def start_target(target: Path) -> Popen:
    try:
        return Popen([str(target)], cwd=str(target.parent))
    except OSError as exc:
        print(f"启动失败: {exc}")
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sim8.exe 资源监控脚本")
    parser.add_argument("--interval", type=int, default=300, help="采样间隔(秒)，默认300")
    parser.add_argument("--hours", type=int, default=72, help="持续时间(小时)，默认72")
    parser.add_argument("--exe", type=str, default="Sim8.exe", help="目标程序名，默认Sim8.exe")
    parser.add_argument("--name", type=str, default="kezuipingsgu", help="展示用目标名")
    parser.add_argument("--csv", type=str, default="monitor_log.csv", help="CSV输出文件名")
    args = parser.parse_args()

    target = (Path.cwd() / args.exe).resolve()
    csv_path = (Path.cwd() / args.csv).resolve()

    log("监控脚本启动")
    ensure_target(target)
    proc_handle = start_target(target)
    pid = proc_handle.pid
    proc = psutil.Process(pid)

    print("=" * 52)
    print("  可信度评估软件 - 进程资源监控工具 v1.0")
    print(f"  监控目标: {args.name} (PID: {pid})")
    print(f"  采样间隔: {args.interval} 秒 | 计划持续: {args.hours} 小时")
    print("=" * 52)

    log("正在检测目标进程...")
    ready_wait = 0
    while ready_wait < 30:
        if proc.is_running():
            break
        time.sleep(1)
        ready_wait += 1

    if not proc.is_running():
        log("目标进程未就绪，监控终止")
        return 1

    log(f"目标进程已就绪  PID={pid}  状态={status_text(proc)}")
    log(f"日志文件已创建: ./{csv_path.name}")
    log("开始写入CSV表头...")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "sample_no", "pid", "memory_mb", "cpu_percent", "status"])
        f.flush()
        log("表头写入完成")
        print("-" * 52)

        # 预热 CPU 统计，避免首个样本总为 0
        proc.cpu_percent(interval=None)
        total_seconds = args.hours * 3600
        max_samples = total_seconds // args.interval if args.interval > 0 else 0
        if max_samples <= 0:
            max_samples = 1

        for i in range(1, int(max_samples) + 1):
            if not proc.is_running():
                log(f"[采样 #{i}]   PID={pid}  进程已退出，停止监控")
                break

            rss_mb = proc.memory_info().rss / 1024 / 1024
            cpu = proc.cpu_percent(interval=0.2)
            st = status_text(proc)
            ts = now_str()
            writer.writerow([ts, i, pid, f"{rss_mb:.1f}", f"{cpu:.1f}", st])
            f.flush()
            print(
                f"[{ts}] [采样 #{i}]"
                f"{' ' * max(1, 5 - len(str(i)))}"
                f"PID={pid}  内存={rss_mb:.1f} MB  CPU={cpu:4.1f}%  状态={st}  ✔ 已写入"
            )

            if i < max_samples:
                time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
