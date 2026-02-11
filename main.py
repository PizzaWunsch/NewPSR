
if __name__ == "__main__":
    import multiprocessing as mp
    mp.set_start_method("spawn", force=True)
    from gui.app import RecorderGUI
    RecorderGUI().run()