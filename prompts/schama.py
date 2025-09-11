import os 

file_path = 'data/temp/dir/file.txt'
dir_path = 'data/temp/dir'
non_existent_path = 'non_exist'



# ディレクトリがない場合は作る
if os.path.isdir(dir_path) == False:
    os.mkdir(dir_path)


print(os.path.isdir(dir_path))