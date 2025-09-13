from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules('mysql.connector')
datas = collect_data_files('mysql.connector')