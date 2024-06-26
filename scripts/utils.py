import sqlalchemy
import psycopg2
import logging
from sqlalchemy import create_engine
#from sqlalchemy.engine import Engine
#from sqlalchemy.orm import sessionmaker
from pathlib import Path
from configparser import ConfigParser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from airflow.models import DAG, Variable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_api_credentials(file_path: Path, section: str) -> dict:
    """
    Lee las credenciales de la api desde el archivo "config.ini"
    
    args: 
        file_path: ruta del archivo de configuración
        section: sección del archivo con la información requerida
        
    Return:
        token de la API para construir el connection string
    """
    config = ConfigParser()
    config.read(file_path)
    api_credentials = dict(config[section])
    return api_credentials

def connect_to_db(config_file, section):
    """
    Crea una conexión a la base de datos especificada en el archivo de configuración.

    Parameters:
    config_file (str): La ruta del archivo de configuración.
    section (str): La sección del archivo de configuración que contiene los datos de la base de datos.

    Returns:
    sqlalchemy.engine.base.Engine: Un objeto de conexión a la base de datos.
    """
    try:
        parser = ConfigParser()
        parser.read(config_file)

        db = {}
        if parser.has_section(section):
            params = parser.items(section)
            db = {param[0]: param[1] for param in params}

            logging.info("Conectándose a la base de datos...")
            conn_str = f"postgresql://{db['user']}:{db['pwd']}@{db['host']}:{db['port']}/{db['dbname']}"
            engine = create_engine(
                conn_str
                , connect_args={"options": f"-c search_path={db['schema']}"}
                )
            
            logging.info("Conexión a la base de datos establecida exitosamente")
            return engine

        else:
            # raise Exception(f"No se encontró la sección {section} en el archivo {config_file}")
            logging.error(f"No se encontró la sección {section} en el archivo {config_file}")
    
    except Exception as e:
        logging.error(f"Error al conectarse a la base de datos: {e}")
        return None

# Nueva función ENEVIAR 
def enviar(context):
    # SMTP server configuration
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'tomasmartindl@gmail.com'  
    receiver_email = 'tomasmartindl@gmail.com'  
    password = Variable.get('GMAIL_SECRET')  
    
    # Determine the status of the task
    task_instance = context['task_instance']
    task_success = task_instance.state == 'success'
    status = "executed successfully" if task_success else "failed"

    # Email subject and body
    subject = f'Airflow Report: Task {task_instance.task_id} {status}'
    body_text = f'The task {task_instance.task_id} on DAG {task_instance.dag_id} scheduled at {context["execution_date"]} has {status}.'
    
    # Setup the email message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = subject
    message.attach(MIMEText(body_text, 'plain'))
    
    # Attempt to send the email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
            print('Email sent successfully!')
    except Exception as e:
        print(f'An error occurred while sending email: {e}')


def load_to_sql(df, table_name, engine, if_exists="replace"):
    """
    Carga un DataFrame en la base de datos especificada.

    Parameters:
    df (pandas.DataFrame): El DataFrame a cargar en la base de datos.
    table_name (str): El nombre de la tabla en la base de datos.
    engine (sqlalchemy.engine.base.Engine): Un objeto de conexión a la base de datos.
    if_exists (str): "append OR replace"
    """
    try:
        logging.info("Cargando datos en la base de datos...")
        df.to_sql(
            table_name,
            engine,
            if_exists=if_exists,
            index=False,
            method="multi"
            )
        logging.info("Datos cargados exitosamente en la base de datos")
    except Exception as e:
        logging.error(f"Error al cargar los datos en la base de datos: {e}")