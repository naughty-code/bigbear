while read i ; do $i ; done < '.env'
flask run --host=0.0.0.0