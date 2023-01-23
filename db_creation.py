import psycopg2
from config import config


def connect():
    connection = None
    try:
        params = config()
        print("connecting to postgresql databse...")
        connection = psycopg2.connect(
        host="localhost",
        database="stocks",
        user="postgres",
        password="1234")

    # create a cursor
        crsr = connection.cursor()
        print('postgresql database version: ')
        crsr.execute('SELECT version()')
        db_version = crsr.fetchone()
        print(db_version)
        crsr.close()

        cur = connection.cursor()

        cur.execute('''  SELECT *
        FROM pg_catalog.pg_tables
        WHERE schemaname != 'pg_catalog' AND 
            schemaname != 'information_schema';
        ''')

        print(cur.fetchall())

        # cur.execute(''' drop table portfolio; ''')
        # cur.execute(''' drop table stock_transactions; ''')
        # cur.execute(''' drop table bank_transaction; ''')
        # cur.execute(''' drop table user_data; ''')
        # cur.execute(''' drop table users; ''')


        cur.execute(''' create table users
                        (
                            unique_id serial primary key,
                            username varchar(50) UNIQUE,
                            password_hash varchar 
                        ); ''')


        cur.execute('''create table user_data
                        (
                            name varchar(30),
                            phone_No varchar(10),
                            email_id varchar(30),
                            dob date,
                            bank_acc_no varchar(30),
                            age int,
                            total_cash real,
                            unique_id int references users(unique_id) ON DELETE CASCADE,
                            primary key (unique_id)
                        ); ''')

        cur.execute(''' create table bank_transaction
                        (
                            bank_transaction_id varchar(100),
                            bank_name varchar(20),
                            amount real,
                            d_or_w char,
                            tstamp timestamp,
                            unique_id int references users(unique_id),
                            primary key (bank_transaction_id)
                        );''')


        cur.execute(''' create table stock_transactions
                        (
                            transaction_id serial,
                            cost real,
                            tstamp timestamp with time zone,
                            symbol varchar(20),
                            units int,
                            unique_id int references users(unique_id),
                            primary key (transaction_id)
                        );''')


        cur.execute(''' create table portfolio
                        (
                            stock_name varchar,
                            stock_symbol varchar(20),
                            units_holding int,
                            average_price real,  
                            unique_id int references users(unique_id),
                            primary key (unique_id, stock_symbol)
                        );  ''')


        connection.commit()
        connection.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if connection is not None:
            connection.close()
            print("database connection terminated")


if __name__ == "__main__":
    connect()
