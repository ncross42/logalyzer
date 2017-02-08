#!/usr/bin/python
import sys, json, glob, os, mysql.connector
from datetime import datetime, date, timedelta
from mysql.connector import errorcode
from pprint import pprint, pformat
import logging

def setup_logger(logger_name, log_file, level=logging.INFO) :# {{{
  l = logging.getLogger(logger_name)
  formatter = logging.Formatter('%(asctime)s : %(message)s')
  fileHandler = logging.FileHandler(log_file, mode='w')
  fileHandler.setFormatter(formatter)
  streamHandler = logging.StreamHandler()
  streamHandler.setFormatter(formatter)

  l.setLevel(level)
  l.addHandler(fileHandler)
  l.addHandler(streamHandler)    
# }}}

BIN_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'

config = {
  'host': '127.0.0.1',
  'user': 'root',
  'password': '',
  'database': '',
  'autocommit' : True,
  'get_warnings': True,
  'raise_on_warnings': True,
  #'use_pure': False,
}

tableLog = 'access_logs_archive'
tableStat = 'prd_daily_stat'

with open(BIN_PATH+'../config/default.json') as default_file:    
  default = json.load(default_file)

try:
  config['host'] = default['mysql']['host']
  config['user'] = default['mysql']['user']
  config['password'] = default['mysql']['password']
  config['database'] = default['mysql']['database']
  cnx = mysql.connector.connect(**config)
  cursor = cnx.cursor() #prepared=True
  cursor.execute('SET sql_log_bin = 0')
except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    print("Something is wrong with your user name or password")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    print("Database does not exist")
  else:
    print(err)
    exit(1)

def get_stat(ymd, pat) :
  sql='''SELECT 
      cc2, COUNT(1) tot, COUNT(DISTINCT ip) uni 
    FROM %s partition(p%s)
    WHERE req_base LIKE '%s' 
    GROUP BY 1''' % (tableLog, ymd, pat)
  try :
    cursor.execute(sql)
    return cursor.fetchall()
  except mysql.connector.Error as err:
    print(err)
    exit(1)

def set_stat (ymd, prod, stat):
  sql='''INSERT INTO %s
    ( d, product, action, cc2, tot, uni )
    VALUES
    ( '%s', '%s', 'download', %%s, %%s, %%s )''' % ( tableStat, ymd, prod )
  try :
    cursor.execute('LOCK TABLE '+tableStat+' WRITE')
    for (cc2,tot,uni) in stat :
      cursor.execute(sql, (cc2,tot,uni) )
    cursor.execute('UNLOCK TABLES')
  except mysql.connector.Error as err:
    log1.error( pformat([err,sql], indent=4) )

prod_pattern = {# {{{
  'player'  : '%gomplayer%.exe',
  'audio'   : '%gomaudio%.exe',
  'pack'    : '%gompack%.exe',
  'recoder' : '%gomrecoder%.exe',
  'encoder' : '%gomencoder%.exe',
  'tv'	    : '%gomtv%.exe',
  'remote'  : '%gomremote%.exe',
  'cam'	    : '%gomcam%.exe',
  'studio'  : '%gomstudio%.exe',
  'mix'	    : '%gommix%.exe',
  'anti'    : '%gomanti%.exe',
  'bridge'  : '%gombridge%.exe',
  'helper'  : '%gomhelper%.exe'
}# }}}

if __name__ == "__main__":
  today = date.today()
  setup_logger('log1', BIN_PATH+'log.stat_download.'+today.strftime('%y%m%d') )
  #setup_logger('log2', BIN_PATH+'log.stat_download.'+today.strftime('%y%m%d') )
  log1 = logging.getLogger('log1')
  #log2 = logging.getLogger('log2')

  startday = today - timedelta(days=1)
  if 1 < len(sys.argv) :
    startday = datetime.strptime( sys.argv[1], '%y%m%d' ).date()
  delta = today - startday

  for d in [startday + timedelta(days=x) for x in range(0,delta.days)] :
    ymd = d.strftime('%y%m%d')
    print ymd
    for prod in prod_pattern :
      ts_start = datetime.now()
      stat = get_stat ( ymd, prod_pattern[prod] )
      #pprint( [prod,stat] )
      set_stat ( ymd, prod, stat )
      log = "end: %s\t%d\t%s" % (prod, len(stat), str(datetime.now()-ts_start) )
      print log

cursor.close()
cnx.close()