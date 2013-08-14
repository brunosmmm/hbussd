<!DOCTYPE html>
<html>
    <head>
        <title>HBUS Server</title>
        <style type="text/css">
        <!--
        @import url("/static/style.css");
        -->
        </style>
    </head>

<div class="hbusContainer">

    <header class="hbusMHeader">
        <section>
            <a href="/" class="hbusLogo">HBUS</a>
        </section>
        <aside>
            <div class="hbusStatus">
                
                <div class = "activeSlaveCount">{{masterStatus.activeSlaveCount}}</div>
                <div class = "statusText">Dispositivos <br /> ativos</div>
                
            </div>
            
            <div class="hbusStatus">
                
            </div>
        </aside>
    </header>
    
    <section class="hbusDeviceDescription">
        <a class="left" href="/slave-uid/{{hex(slave.hbusSlaveUniqueDeviceInfo)}}">{{slave.hbusSlaveDescription}}</a>
        <div class="right">Objeto {{objectNumber}}</div>
    </section>
    
    <div class="hbusMMain">
        
        
        
    </div>
    
</div>
        
</html>
