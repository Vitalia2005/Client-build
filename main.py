import shutil
import urllib.parse
import requests
import subprocess
import gitlab
import base64
import os, os.path
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import sys

rgzs_and_gpfs  = []

# Конфигурация
current_directory = os.getcwd()
GITLAB_URL = '' # url gitlab
PRIVATE_TOKEN = ''  # your gitlab token

PROJECT_ID = '1138'  # берём в settings - general нужной репы.
BRANCH_NAME = 'pts'  # ветка
# BRANCH_NAME = get_current_git_branch()
# PRIVATE_TOKEN = sys.argv[1] # your gitlab token
#
# PROJECT_ID = sys.argv[2] # берём в settings - general нужной репы. 1138 ру / 1170 еу
# BRANCH_NAME = sys.argv[3] # ветка

# Директория для сохранения измененных файлов в последнем коммите
OUTPUT_DIR = rf'{current_directory}\changed_files'

# if str(current_directory).split('\\')[-1] == 'ROTEU':
#     PROJECT_ID = '1170'


# Папка из которой будет делаться gpf rgz
folder_to_add = rf"{current_directory}\gameFolder"
print(folder_to_add)

# Создание заголовков для API запросов
headers = {
    'PRIVATE-TOKEN': PRIVATE_TOKEN
}

# Путь к консольному приложению GRF editor
GRF_EDITOR_PATH = r"C:\Users\vitaliya.bazanova\Desktop\Debug\GrfCL.exe"

# Куда будут сохраняться архивы. Конечная папка
SAVE_GRF_PATH = rf'{current_directory}\patch'

if os.path.exists(SAVE_GRF_PATH):
    shutil.rmtree(SAVE_GRF_PATH)
os.makedirs(SAVE_GRF_PATH)
PATCH_TXT_PATH = rf'{SAVE_GRF_PATH}\patch.txt'

error_lubs_compile = []
params = {
    'ref': BRANCH_NAME
}

downloaded_files_list = []


# Функция для создания коммита
def create_commit(file_paths, commit_message, lubs):
    # Создание объекта GitLab
    gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)

    # Получение проекта
    project = gl.projects.get(PROJECT_ID)

    # Чтение файла в бинарном режиме
    actions = []
    for file_path in file_paths:
        with open(file_path, "rb") as file:
            file_content = file.read()

            # Кодирование содержимого файла в Base64
            encoded_content = base64.b64encode(file_content).decode()
            actions.append({
                'action': 'create',
                'file_path': f'patch/{file_path.split('\\')[-1]}',
                'content': encoded_content,
                'encoding': 'base64',  # Указываем, что файл передается в Base64
            })
    file_path = 'patch/patch.txt'
    with open(PATCH_TXT_PATH, "rb") as file:
        file_content = file.read()
        encoded_content = base64.b64encode(file_content).decode()
        actions.append({
            'action': 'update',
            'file_path': file_path,
            'content': encoded_content,
            'encoding': 'base64',  # Указываем, что файл передается в Base64
        })
    for file_path in lubs:
        print(f'ЛУБ ФАЙЛ {file_path} and {lubs[file_path]}')
        try:
            with open(file_path, "rb") as file:
                file_content = file.read()
                # Кодирование содержимого файла в Base64
                encoded_content = base64.b64encode(file_content).decode()

                # Создание URL запроса
                url = f"{GITLAB_URL}/projects/{PROJECT_ID}/repository/files/{lubs[file_path]}"
                print(url)

                # Параметры запроса
                params = {
                    "ref": BRANCH_NAME
                }

                # Выполнение запроса
                response = requests.get(url, headers=headers, params=params)

                # Проверка существует ли файл
                try:
                    file = project.files.get(file_path=lubs[file_path], ref=BRANCH_NAME)
                    actions.append({
                        'action': 'update',
                        'file_path': f'{lubs[file_path]}',
                        'content': encoded_content,
                        'encoding': 'base64',  # Указываем, что файл передается в Base64
                    })
                except gitlab.exceptions.GitlabGetError:
                    print("Файл не найден")
                    actions.append({
                        'action': 'create',
                        'file_path': f'{lubs[file_path]}',
                        'content': encoded_content,
                        'encoding': 'base64',  # Указываем, что файл передается в Base64
                    })
                # if response.status_code == 200:
                #
                # elif response.status_code == 400:
                #
                # else:
                #     print(f"Ошибка: {response.status_code}, {response.text}")



        except FileNotFoundError:
            print(f'Файл {file_path} не найден')

    # Создание коммита
    commit_data = {
        'branch': BRANCH_NAME,
        'commit_message': commit_message,
        'actions': actions
    }

    commit = project.commits.create(commit_data)
    print("Коммит успешно создан!")
    # Получение информации о коммите
    commit_info = project.commits.get(commit.id)
    commit_date = commit_info.committed_date

    return commit_date


# Пример использования функции для коммита и пуша
def commit(files_to_commit, lubs):
    # Сообщение коммита
    commit_message = "(AUTO) Add client patch things"

    # Создание коммита и пуш
    commit_date = create_commit(files_to_commit, commit_message, lubs)
    # Записываем в спец файлик дату последнего коммита
    filenamer = 'internal/last_client_build_commit_date.txt'
    p = f'{current_directory}/last_client_build_commit_date.txt'
    with open(p, 'w', encoding='utf-8') as f:
        f.write(datetime.fromisoformat(commit_date).isoformat("T", "seconds") + 'Z')
    # Создание объекта GitLab
    gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)
    project = gl.projects.get(PROJECT_ID)
    with open(p, "rb") as file:
        file_content = file.read()
        encoded_content = base64.b64encode(file_content).decode()
        actions1 = [{
            'action': 'update',
            'file_path': f'{filenamer}',
            'content': encoded_content,
            'encoding': 'base64',  # Указываем, что файл передается в Base64
        }]
    # Создание коммита
    commit_data = {
        'branch': BRANCH_NAME,
        'commit_message': '(AUTO) update last_client_commit date',
        'actions': actions1
    }

    project.commits.create(commit_data)
    print("Коммит дат успешно создан!")


# функция для получения текущей ветки гита
def get_current_git_branch():
    # Запуск команды в командной строке и получение вывода
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)

    # Проверяем, успешно ли выполнена команда
    if result.returncode == 0:
        # Возвращаем имя текущей ветки
        b = result.stdout.strip()
        print('Ветка', b)
        return b
    else:
        # В случае ошибки возвращаем сообщение об ошибке
        return f"Ошибка: {result.stderr.strip()}"


# функция для подсчета сегодняшних гпф ргз
def count_files():
    gpf_files = 0
    rgz_files = 0
    r = []

    url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/repository/tree"
    # Параметры запроса
    params = {
        'path': 'patch',  # Укажите путь к нужной папке
        'ref': BRANCH_NAME,  # Ветка проекта
        'per_page': 100,  # Количество элементов на странице (опционально)
    }
    counfiles = 1000
    names = []

    # Осуществляем запрос
    for i in range(1, (counfiles // 100) + 2):
        params['page'] = i
        if i == (counfiles // 100) + 1:
            params['per_page'] = counfiles % 100 if counfiles % 100 != 0 else 1
        response = requests.get(url, headers=headers, params=params)
        files = response.json()

        # Вывод списка файлов
        for file in files:
            names.append(file['name'])
    for filed in names:
        if filed.startswith(datetime.now().strftime("%Y%m%d")):
            if filed.endswith(".rgz"):
                rgz_files += 1
            elif filed.endswith(".gpf"):
                gpf_files += 1
    print('????????????', rgzs_and_gpfs)
    for filed in rgzs_and_gpfs:
        if datetime.now().strftime("%Y%m%d") in filed:
            if filed.endswith(".rgz"):
                rgz_files += 1
            elif filed.endswith(".gpf"):
                gpf_files += 1

    return gpf_files, rgz_files


def prepend_to_file_patch_txt(patch_txt_path, files_list):
    # Получаем сегодняшнюю дату в формате 'дд.мм.гг'
    today_date = datetime.now().strftime('%d.%m.%y')

    # Формируем строки, которые нужно добавить
    first_line = f'//========{today_date}\n'
    second_line = f''  # Файлы
    for u, el in enumerate(files_list):
        second_line += f'{u + 1} {el.split('\\')[-1]}\n'
        print(second_line)

    # Читаем содержимое файла
    with open(patch_txt_path, 'r+', encoding='ANSI') as file:
        content = file.readlines()

        # Проверяем, есть ли сегодняшняя дата на первой строке
        if content and content[0].strip() == first_line.strip():
            # Если дата уже есть, добавляем только файлы
            content.insert(1, second_line)
        else:
            # Если даты нет, добавляем обе строки в начало
            content.insert(0, second_line)
            content.insert(0, first_line)

        # Возвращаем курсор в начало файла и записываем обратно
        file.seek(0)
        file.writelines(content)


def create_gpf_archive(folder_to_add):
    try:
        # Формируем имя файла на основе текущей даты
        current_date = datetime.now().strftime("%Y%m%d")
        output_path = f"{SAVE_GRF_PATH}\\{current_date}_{count_files()[0] + 1}.gpf"

        # Создаем GPF архив из папки
        subprocess.run([GRF_EDITOR_PATH, '-makeGrf', output_path, folder_to_add, '949'], check=True)

        print(f"GPF архив успешно создан: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при выполнении команды: {e}")


# Пример использования
# folder_to_add = r"C:\Users\vitaliya.bazanova\PycharmProjects\pythonProject3\clientbuild\changed_files\gameFolder\"
# create_gpf_archive(folder_to_add)

def create_rgz_archive(folder_to_add):
    try:
        # Формируем имя файла на основе текущей даты
        print(folder_to_add)
        current_date = datetime.now().strftime("%Y%m%d")
        output_path = f"{SAVE_GRF_PATH}\\{current_date}_{count_files()[1] + 1}.rgz"

        # Создаем RGZ архив из папки
        print(f'{GRF_EDITOR_PATH} -makeRgz {output_path} {folder_to_add} 949')
        subprocess.run([GRF_EDITOR_PATH, '-makeRgz', output_path, folder_to_add, '949'], check=True)

        print(f"RGZ архив успешно создан: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
    return None


# Пример использования
# folder_to_add = r"C:\Users\vitaliya.bazanova\PycharmProjects\pythonProject3\clientbuild\changed_files\gameFolder\data"
# create_rgz_archive(folder_to_add)


# Функция для изменения кодировки в CMD
def change_cmd_encoding(encoding_code):
    try:
        # Запуск команды chcp с указанным кодом кодировки
        result = subprocess.run(['chcp', str(encoding_code)], text=True, check=True, shell=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error changing encoding: {e}")


# change_cmd_encoding('65001')

def change_encoding(encoding_code):
    try:
        # Запуск команды chcp с указанным кодом кодировки
        subprocess.run(f'{GRF_EDITOR_PATH} -enc {encoding_code}', check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error changing encoding: {encoding_code}")


# change_encoding('65001')
# Функция для получения последнего коммита
count_commits = 5000  # количество коммитов


def get_commits():
    url = f'{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/repository/commits'
    print(url)
    r = []
    # SINCE_DATE = last_commit()
    params = {
        'ref_name': BRANCH_NAME,
        'per_page': 100,
        'since': last_commit()}
    for i in range(1, (count_commits // 100) + 2):
        params['page'] = i
        if i == (count_commits // 100) + 1:
            params['per_page'] = count_commits % 100 if count_commits % 100 != 0 else 1
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        r += response.json()
    print(r)
    return r


# Функция получает дату последнего коммита который трогала данная программа (начиная с этого коммита будут браться изменения)
def last_commit():
    filename = 'internal/last_client_build_commit_date.txt'
    download_file(f'internal/last_client_build_commit_date.txt',
                  f'{current_directory}/last_client_build_commit_date.txt')
    p = f'{current_directory}/last_client_build_commit_date.txt'
    with open(p, 'r', encoding='utf-8') as f:
        d = f.readline()

        # Исходная дата в строковом формате ISO
        iso_date = d.replace('Z', '').strip()

        # Преобразуем строку в объект datetime
        date_time_obj = datetime.fromisoformat(iso_date)

        # Прибавляем одну секунду
        new_date_time_obj = date_time_obj + timedelta(seconds=1)

        # Преобразуем обратно в строку в формате ISO
        new_iso_date = new_date_time_obj.isoformat()

        return new_iso_date + 'Z'


# Функция для получения измененных файлов из коммита
def get_changed_files(commit_id):
    url = f'{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/repository/commits/{commit_id}/diff'
    all_files = []
    page = 1

    while True:
        params = {'page': page, 'per_page': 100}  # Указываем количество файлов на страницу, например 100
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        all_files.extend(data)  # Добавляем полученные файлы в общий список
        if len(data) < 100:  # Если получено меньше, чем 100 файлов, значит больше страниц нет
            break
        page += 1

    return all_files


# Функция для загрузки файла

FAILED = 0
DOWNLOADED_FILES = 0
COUNTER = -1


def copy_file(source_path, destination_folder):
    # Проверяем, существует ли исходный файл
    if not os.path.isfile(source_path):
        print(f"Файл {source_path} не существует.")
        return

    # Проверяем, существует ли папка назначения
    if not os.path.exists(destination_folder):
        print(f"Папка назначения {destination_folder} не существует. Создаём её.")
        os.makedirs(destination_folder)

    # Определяем путь назначения
    destination_path = os.path.join(destination_folder, os.path.basename(source_path))

    # Копируем файл
    try:
        shutil.copy2(source_path, destination_path)
    except Exception as e:
        print(f"Произошла ошибка при копировании файла: {e}")


# Компиляция lua в lub
def compile_lua_to_lub(lua_file_path, lub_file_path=None):
    global error_lubs_compile
    # Проверка существования исходного файла
    if not os.path.exists(lua_file_path):
        for fff in downloaded_files_list:
            try:
                os.remove(fff)
            except Exception:
                pass
        raise FileNotFoundError(f"Файл {lua_file_path} не найден.")

    # Если путь к lub файлу не указан, то заменить расширение .lua на .lub
    if lub_file_path is None:
        lub_file_path = lua_file_path.replace('.lua', '.lub')

    # Формирование команды для выполнения
    command = ['luac', '-o', lub_file_path, lua_file_path]

    try:
        # Выполнение команды
        subprocess.run(command, check=True)
        print(f"Файл {lub_file_path} успешно создан.")
        print()
        return lub_file_path

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при компиляции: {lua_file_path}")
        error_lubs_compile.append(lua_file_path)
        for fff in downloaded_files_list:
            try:
                os.remove(fff)
            except Exception:
                pass
        raise e
    except FileNotFoundError:
        for fff in downloaded_files_list:
            try:
                os.remove(fff)
            except Exception:
                pass
        raise ValueError(
            "Команда 'luac' не найдена. Убедитесь, что Lua установлена и путь к 'luac' добавлен в переменную окружения PATH.")


def download_file(file_path, output_path, pr_id=PROJECT_ID, par=params):
    global FAILED, COUNTER

    url = f'{GITLAB_URL}/api/v4/projects/{pr_id}/repository/files/{urllib.parse.quote(str(file_path), safe='')}/raw'
    # params = {
    #     'ref': BRANCH_NAME
    # }
    response = requests.get(url, headers=headers, params=par)
    print()

    if response.status_code == 200:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            with open(output_path, 'wb') as file:
                file.write(response.content)
                COUNTER += 1
            print(f'{COUNTER}. Downloaded {file_path} to {output_path}')
            downloaded_files_list.append(output_path)
        except Exception:
            FAILED += 1
            print(f'FAILED {file_path} to {output_path}: {response.status_code} {response.text}')
    else:
        print(f'Failed to download {file_path}: {response.status_code} {response.text}')
        FAILED += 1


def delete_all_trash():
    folders = ['changed_files', 'patch', 'tmp']
    for f in folders:
        try:
            shutil.rmtree(os.path.join(current_directory, f))
        except Exception:
            pass
    for filenames in os.listdir(current_directory):
        # Проверяем, является ли файл файлом .dll
        if filenames.endswith('.dll'):
            file_path = os.path.join(current_directory, filenames)
            os.remove(file_path)
    for fff in downloaded_files_list:
        try:
            os.remove(fff)
        except Exception:
            pass
    try:
        shutil.rmtree(f'{OUTPUT_DIR}\\gameFolder\\System')
    except OSError as e:
        print(e)
    try:
        shutil.rmtree(f'{OUTPUT_DIR}\\gameFolder\\data')
    except Exception as e:
        print(e)


# Главная функция
def main():
    global DOWNLOADED_FILES
    lubs_files = {}
    commits = get_commits()
    changed_files = set()
    commit_date = '2022-01-01T11:35:40Z'

    for commit in commits:
        commit_id = commit['id']
        if datetime.fromisoformat(commit['created_at']) > datetime.fromisoformat(commit_date):
            commit_date = commit['created_at']
        if not commit['title'].startswith('Merge'):
            diffs = get_changed_files(commit_id)
            for diff in diffs:
                changed_files.add(diff['new_path'])
        else:
            print('Пропускаем мердж')

    folders = set()
    gamefolder_files_folders = []
    for file_path in changed_files:
        file_path_list = file_path.split('/')
        folders.add(file_path_list[0])
        try:
            folders.add(file_path_list[1])
        except Exception:
            pass
        if file_path_list[0] == 'gameFolder':
            if file_path_list[1].lower() != 'system' and file_path_list[1].lower() != 'data':
                gamefolder_files_folders.append(file_path_list[1])
            output_path = os.path.join(OUTPUT_DIR, file_path)
            download_file(file_path, output_path)
            if file_path.endswith('.lua'):
                t = compile_lua_to_lub(output_path)
                print(t)
                lubs_files[t] = 'gameFolder' + t.split("gameFolder", 1)[-1]
                os.remove(os.path.join(OUTPUT_DIR, file_path))

            DOWNLOADED_FILES += 1

    files = []
    gpfs_and_rgzs = []
    print('FOLDER!!!!!!!!!!!', folders)
    if 'gameFolder' in folders:

        if 'data' in folders:
            name = create_gpf_archive(f'{OUTPUT_DIR}\\gameFolder\\data')
            if name:
                files.append(name)
                rgzs_and_gpfs.append(name)
                gpfs_and_rgzs.append(name.split('\\')[-1])
        if 'System' in folders:
            name = create_rgz_archive(f'{OUTPUT_DIR}\\gameFolder\\System')
            rgzs_and_gpfs.append(name)
            if name:
                files.append(name)
                gpfs_and_rgzs.append(name.split('\\')[-1])
        if gamefolder_files_folders:
            name = create_rgz_archive(f'{OUTPUT_DIR}\\gameFolder')
            rgzs_and_gpfs.append(name)
            if name:
                files.append(name)
                gpfs_and_rgzs.append(name.split('\\')[-1])

        download_file('patch/patch.txt', PATCH_TXT_PATH)
        prepend_to_file_patch_txt(PATCH_TXT_PATH, files)
    return files, lubs_files


if __name__ == '__main__':
    try:
        shutil.rmtree(OUTPUT_DIR)
    except Exception:
        pass
    try:
        commit_files, lubs = main()
        print(f'FAILED files {FAILED}')
        print(f'download {DOWNLOADED_FILES} files')
        commit(commit_files, lubs)

        # Убираем все dll (без понятия что их создает)
        for filename in os.listdir(current_directory):
            if filename == 'changed_files':
                shutil.rmtree(os.path.join(current_directory, filename))

            # Проверяем, является ли файл файлом .dll
            if filename.endswith('.dll'):
                file_path = os.path.join(current_directory, filename)
                os.remove(file_path)

        for fff in downloaded_files_list:
            try:
                os.remove(fff)
            except Exception:
                pass

        try:
            shutil.rmtree(os.path.join(current_directory, 'tmp'))
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))
        print(f'ПРОИЗОШЛО {len(error_lubs_compile)} ОШИБОК КОМПИЛЯЦИИ LUB')
        for i, el in enumerate(error_lubs_compile):
            print(f'{i + 1}) {el}')
        shutil.rmtree(SAVE_GRF_PATH)
    except Exception as e:
        delete_all_trash()
        raise e