# 2018FA-CSIS-250-3580-Project2

## A demo sensor, using the Timezone API

Inheriting from SensorX, foo sensor is a simple software sensor, using the web service available at 
http://api.timezonedb.com/, which is documented here: https://timezonedb.com/api

While the imposed rate limit is one request per second, for this demo, 
I have set the rate limit to 10

Therefore, the sensor will request a new timestamp for the "America/Los_Angeles" timezone, 
when asked, but not more frequently than once per ten seconds.

To provide a value, even after a re-start (with a down-time of less than 10 secs), or during request in between the 
10 second window, the processed webservice data gets _cached_ as a text file.

   