import sys
import os
import shutil
import logging
import sqlite3
import json
import tempfile
import subprocess
import csv

TOOL = "openssl"

TOKEN_NOT_SET = 2
CONNECT_ERROR = 3
SERVER_ERROR = 4

CONF_ERROR = 21
FOLDER_ERROR = 22

DB_NAME = "nas_sign.db"
DB_SIG_NAME = "nas_sign.sig"
KEY_SIG_NAME = "pub_key.sig"

if TOOL == "openssl":
    KEY_NAME = "pub_key.pem"
elif TOOL == "gpg":
    KEY_NAME = "pub_key.gpg"

def get_token():
    if "QNAP_CODESIGNING_TOKEN" not in os.environ:
        logging.error("Environment variable QNAP_CODESIGNING_TOKEN not set")
        sys.exit(TOKEN_NOT_SET)
    return os.environ["QNAP_CODESIGNING_TOKEN"]

def config_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def check_is_db(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()
    except sqlite3.DatabaseError:
        logging.error("%s is not a valid sqlite db" % db_file)
        sys.exit(1)

def check_args(kwargs):
    if "db" in kwargs and os.path.isfile(kwargs["db"]):
        check_is_db(kwargs["db"])
    if "csv" in kwargs and not os.path.isfile(kwargs["csv"]):
        logging.error("cannot find csv file")
        sys.exit(1)
    if "rootkeyfile" in kwargs and kwargs["rootkeyfile"] == "":
        logging.error("parameter rootkeyfile not provided")
        sys.exit(1)
    if "tgzfile" in kwargs and not os.path.isfile(kwargs["tgzfile"]):
        logging.error("cannot find tgz file %s" % kwargs["tgzfile"])
        sys.exit(1)
    if "version" in kwargs and kwargs["version"] == "":
        logging.error("firmware version number not provided")
        sys.exit(1)

def check_cwd(kwargs):
    if not os.path.isdir(kwargs["cwd"]):
        logging.error("cwd %s is not a directory" % kwargs["cwd"])

def create_db(db):
    sql_create_signature_table = """
        CREATE TABLE SignedFile (
            FileID INTEGER PRIMARY KEY,
            Path TEXT NOT NULL,
            Package TEXT,
            Signature BLOB,
            PublicKeyID INT
        );
    """
    sql_add_path_index = "CREATE INDEX SignedFilePath ON SignedFile (Path);"
    if TOOL == "openssl": 
        sql_create_key_table = """
            CREATE TABLE PublicKey (
                KeyID INTEGER PRIMARY KEY,
                Type TEXT NOT NULL,
                Version TEXT,
                QpkgName TEXT,
                Key TEXT NOT NULL,
                Signature BLOB NOT NULL
            );
        """
    elif TOOL == "gpg":
        sql_create_key_table = """
            CREATE TABLE PublicKey (
                KeyID INTEGER PRIMARY KEY,
                Type TEXT NOT NULL,
                Version TEXT,
                QpkgName TEXT,
                Key BLOB NOT NULL,
                Signature BLOB NOT NULL
            );
        """

    db_folder = os.path.dirname(db)
    if db_folder != "" and not os.path.isdir(db_folder):
        try:
            os.makedirs(db_folder)
        except Exception as e:
            logging.error(str(e) + " when creating folder %s" % db_folder)
            sys.exit(1)
    if os.path.isfile(db):
        try:
            os.remove(db)
        except Exception as e:
            logging.error(str(e) + " when removing file %s" % db)
            sys.exit(1)
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(sql_create_signature_table)
    cur.execute(sql_add_path_index)
    cur.execute(sql_create_key_table)
    conn.commit()
    conn.close()

def read_csv(csv_file):
    try:
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            output = []
            for row in reader:
                if len(row) < 3:
                    continue
                package = unicode(row[0],"utf-8").strip()
                relative_path = unicode(row[1],"utf-8").strip()
                absolute_path = unicode(row[2],"utf-8").strip()
                if package[0] == "#": # a line of comment
                    continue
                output.append([package,relative_path,absolute_path])
            return output
    except Exception as e:
        logging.error(str(e) + " when processing csv")
        sys.exit(1)

def update_packages(db, csv_file):
    # Get paths,packages from csv and insert/update DB
    rows = read_csv(csv_file)

    sql_insert_path = """INSERT INTO SignedFile (Path, Package) SELECT ?, ?
                         WHERE NOT EXISTS (SELECT 1 FROM SignedFile WHERE Path = ?);
    """
    sql_update_package = "UPDATE SignedFile SET Package = ? WHERE Path = ?"

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    for row in rows:
        package = row[0]
        absolute_path = row[2]
        cur.execute(sql_insert_path, (absolute_path, package, absolute_path))
        if cur.rowcount == 0:
            # in case that path already exists in DB, update "Package" value
            cur.execute(sql_update_package, (package, absolute_path))
    conn.commit()
    conn.close()
    logging.info("Paths and Packages from csv updated to codesigning DB %s" % db )

def copy_file(src, dst):
    dst_dir = os.path.dirname(dst)
    if not os.path.exists(dst_dir):
        try:
            os.makedirs(dst_dir)
        except Exception as e:
            logging.error(str(e) + " when creating folder " + dst_dir)
            sys.exit(1)
    shutil.copyfile(src, dst)

def check_for_tgz(temp_folder, output_tgz_file):
    # Check if temp folder or tgz file exists already. Remove it if exists

    if os.path.exists(temp_folder): # if the temp folder exists already
        try:
            shutil.rmtree(temp_folder)
        except Exception as e:
            logging.error(str(e) + " when removing folder %s" % temp_folder)
            sys.exit(1)
    try:
        os.makedirs(temp_folder)
    except Exception as e:
        logging.error(str(e) + " when creating folder %s" % temp_folder)
        sys.exit(1)
    if os.path.exists(output_tgz_file): # if the tgz exists already
        try:
            os.remove(output_tgz_file)
        except Exception as e:
            logging.error(str(e) + " when removing tgz file %s" % output_tgz_file)
            sys.exit(1)

def create_tgz(temp_folder, output_tgz_file):
    # Tar the files in temp folder
    command = "tar -czf %s ."
    command = command % (output_tgz_file)
    sp = subprocess.Popen(command.split(),cwd=temp_folder,stdout=subprocess.PIPE)
    out = sp.communicate()[0]
    if sp.returncode != 0:
        logging.error(out)
        sys.exit(1)
    shutil.rmtree(temp_folder)

def sign_files(kwargs):
    # Upload tgz to code signing server, and return response from server
    server = kwargs["server"]
    key_type = kwargs["key_type"]
    tgz_file_name = kwargs["tgzfile"]
    url = "%s/sign/%s" % (server,key_type)
    if key_type == "fw":
        url = url + "/" + kwargs["version"]
    elif key_type == "qpkg":
        url = url + "/" + kwargs["qpkgname"] + "/" + kwargs["version"]
    command = "curl %s --connect-timeout 60 --max-time 600 -X POST -F token=%s -F file=@%s https://%s"
    if "cert" in kwargs:
        if not os.path.isfile(kwargs["cert"]):
            logging.error("Cannot find certificate file %s" % kwargs["cert"])
            sys.exit(1)
        command = command % ("--cacert %s" % kwargs["cert"],kwargs["token"],tgz_file_name,url)
    else:
        command = command % ("-k",kwargs["token"],tgz_file_name,url)
    try:
        sp = subprocess.Popen(command.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err = sp.communicate()
        if sp.returncode != 0:
            logging.error("curl error %s" % err)
            sys.exit(CONNECT_ERROR)
        response = json.loads(out)
        if response["error"] != 0:
            logging.error("Error message from server: %s" % response["msg"])
            sys.exit(SERVER_ERROR)
        return response
    except Exception as e:
        logging.error("Failed to run curl command")
        sys.exit(1)

def b64_decode(encoded):
    encoded_file = tempfile.NamedTemporaryFile(mode="w")
    encoded_file.write(encoded)
    encoded_file.flush()
    decoded_file = tempfile.NamedTemporaryFile(mode="w+b")
    command = "openssl enc -d -base64 -A -in %s -out %s"
    command = command % (encoded_file.name, decoded_file.name)
    try:
        returncode = subprocess.call(command.split())
        if returncode != 0:
            logging.error("Failed to decode signature of file: %s" % path)
            return None
        else:
            return decoded_file.read()
    except Exception as e:
        logging.error("Failed to run openssl command")
        sys.exit(1)

def add_key_to_db(public_key_dict, sqlite_file_name):
    # put this key into DB and get key ID if key not in DB already
    # otherwise get key ID from DB

    keyid = -1
    key_type = public_key_dict["key_type"]
    qpkgname = public_key_dict["qpkgname"] if "qpkgname" in public_key_dict else ""
    version = public_key_dict["version"]
    if TOOL == "openssl":
        key = public_key_dict["key"]
    elif TOOL == "gpg":
        key = b64_decode(public_key_dict["key"])
    signature = b64_decode(public_key_dict["signature"])
    conn = sqlite3.connect(sqlite_file_name)
    cur = conn.cursor()
    sql_get_key = "SELECT * FROM PublicKey WHERE Type=? AND QpkgName=? AND Version=?;"
    cur.execute(sql_get_key, (key_type,qpkgname,version))
    entry = cur.fetchone()
    if entry == None:
        # Key doesnot exist in DB, insert one and return KeyID
        sql_insert_key = "INSERT INTO PublicKey (Type,QpkgName,Version,Key,Signature) VALUES (?,?,?,?,?);"
        if TOOL == "openssl":
            cur.execute(sql_insert_key, (key_type,qpkgname,version,key,sqlite3.Binary(signature)))
        elif TOOL == "gpg":
            cur.execute(sql_insert_key, (key_type,qpkgname,version,sqlite3.Binary(key),sqlite3.Binary(signature)))
        keyid = cur.lastrowid
    else:
        # Key already exists in DB, return KeyID
        keyid = entry[0]
    conn.commit()
    cur.close()
    conn.close()
    return keyid

def update_signatures(kwargs, server_response):
    if server_response["error"] != 0:
        logging.error("Error message from server: %s" % server_response["msg"])
        sys.exit(1)
    sqlite_file_name = kwargs["db"]
    keyid = add_key_to_db(server_response["public_key"], sqlite_file_name)
    signatures = server_response["signatures"]
    conn = sqlite3.connect(sqlite_file_name)
    cur = conn.cursor()
    sql_update_signature = "UPDATE SignedFile SET PublicKeyID=?, Signature=? WHERE Path=?"
    sql_insert_signature = "INSERT INTO SignedFile (Path,Signature,PublicKeyID) VALUES (?,?,?)"
    for item in signatures:
        file_path = item["file"]
        signature = b64_decode(item["signature"])
        if signature is None:
            continue
        cur.execute(sql_update_signature, (keyid, sqlite3.Binary(signature), file_path))
        if cur.rowcount == 0:
            # The path doesnot exist in DB, insert new one
            cur.execute(sql_insert_signature, (file_path, sqlite3.Binary(signature), keyid))
    conn.commit()
    cur.execute("DELETE FROM SignedFile WHERE Signature IS NULL;")
    conn.commit()
    cur.close()
    conn.close()
    logging.info("Updated signatures to DB %s" % sqlite_file_name)
