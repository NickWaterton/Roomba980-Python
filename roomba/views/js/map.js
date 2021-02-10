/*  global $ alert sizeX sizeY xOffset yOffset updateEvery */
/*  eslint no-unused-vars: "off" */
/*  eslint no-global-assign: "off" */
/*  eslint no-native-reassign: "off" */

window.onload = getMapSize;

var pathLayerContext;
var robotBodyLayerContext;
var textLayerContext;

var pathLayer;
var robotBodyLayer;
var textLayer;

var lastPhase = '';
var mapping = true;

var Dockimg = new Image();
Dockimg.src = '/res/home.png'

var Roombaimg = new Image();
Roombaimg.src = '/res/roomba.png'

var outline = new Image();
var name = 'none';

var xOffset = 0;    //dock location
var yOffset = 0;    //dock location
var sizeX = 0;
var sizeY = 0;
var roombaangle = 0;
var rotation = 0;
var updateEvery = 5000;
var lineWidth = 20;
var maxDim  = 0;
var gXoff = 0;
var gYoff = 0;

var canvasStyle = document.styleSheets[0].cssRules.item(2).style
var maxHeight =  parseInt(canvasStyle.maxHeight, 10);
var orgMaxheight = maxHeight;

function getMapSize () {
  $.getJSON('/api/local/map/mapsize', function( data ) {
    sizeX = data.x;
    sizeY = data.y;
    xOffset = data.off_x;
    yOffset = data.off_y;
    rotation = data.angle;
    roombaangle = data.roomba_angle;
    updateEvery = data.update;
  }).always(function() {
    startApp(); 
  });
}

function getRoombaName () {
  $.getJSON('/api/local/info/name', function( data ) {
    name = data.name;
  }).success(function() {
    $('#name').html(name);
  });
}

function startApp () {
  pathLayer = document.getElementById('path_layer');
  robotBodyLayer = document.getElementById('robot_body_layer');
  textLayer = document.getElementById('text_layer');
  
  Updatevalues();
  getDimentions();
  getRoombaName();
  
  pathLayer.width = maxDim;
  pathLayer.height = maxDim;

  robotBodyLayer.width = maxDim;
  robotBodyLayer.height = maxDim;

  textLayer.width = maxDim;
  textLayer.height = maxDim;
  
  rotation = NaN;    //force rotation update

  pathLayerContext = pathLayer.getContext('2d');
  robotBodyLayerContext = robotBodyLayer.getContext('2d');
  textLayerContext = textLayer.getContext('2d');
  
  UpdateCanvas();
  clearMap();
  startMissionLoop();
}

function getDimentions () {
  maxDim = Math.max(sizeX, sizeY);
  gXoff = (maxDim - sizeX)/2;
  gYoff = (maxDim - sizeY)/2;
}

function getMapOutline () {
  $.get('/api/local/map/outline', function( data ) {
    var pngimg = data;
    console.log('got png image, length: %d',pngimg.length);
    //console.log(pngimg)
    if (pngimg) {
      outline.src = "data:image/png;base64," + pngimg;
      textLayerContext.drawImage(outline, 0, (textLayer.height/2)-(outline.naturalHeight/2));
    }
  });
}

function Updatevalues () {
  $('#sizew').val(sizeX);
  $('#sizeh').val(sizeY);

  $('#offsetx').val(xOffset);
  $('#offsety').val(yOffset);
  
  $('#rotation').val(rotation);
  $('#roombaangle').val(roombaangle);

  $('#updateevery').val(updateEvery);
  $('#linewidth').val(lineWidth);
  
  $('#maxheight').val(maxHeight);
  
  $('#bin').html('no bin');
  console.log('updated values')
}

function UpdateLineWidth () {
  lineWidth = getValue('#linewidth', lineWidth);
  pathLayerContext.lineWidth = lineWidth;
  if (lineWidth == 1) {
    pathLayerContext.strokeStyle = '#000000';
  } else {
    pathLayerContext.strokeStyle = 'lawngreen';
  }
  pathLayerContext.lineCap = 'round';
  pathLayerContext.lineJoin = 'round';
}

function startMissionLoop () {
  if (mapping) {
    $('#mapStatus').html('getting point...');
    $.get('/api/local/info/mission', function (data) {
      messageHandler(data);
      setTimeout(startMissionLoop, updateEvery);
    });
  } else {
    $('#mapStatus').html('stopped');
  }
}

function messageHandler (msg) {
  if (msg.cleanMissionStatus) {
    // firmware version 2/3
    msg.ok = msg.cleanMissionStatus;
    msg.ok.pos = msg.pose;
    msg.ok.batPct = msg.batPct;
    if (msg.bin) {
      $('#bin').html(msg.bin.present);
    }
    $('#nMssn').html(msg.ok.nMssn);
  }
  var d = new Date();
  msg.ok.time = new Date().toLocaleString().split(' ')[1];
  $('#mapStatus').html('drawing...');
  $('#last').html(msg.ok.time);
  $('#mission').html(msg.ok.mssnM);
  $('#cycle').html(msg.ok.cycle);
  $('#phase').html(msg.ok.phase);
  $('#flags').html(msg.ok.flags);
  $('#batPct').html(msg.ok.batPct);
  $('#error').html(msg.ok.error);
  $('#sqft').html(msg.ok.sqft);
  $('#expireM').html(msg.ok.expireM);
  $('#rechrgM').html(msg.ok.rechrgM);
  $('#notReady').html(msg.ok.notReady);
  $('#theta').html(msg.ok.pos.theta);
  $('#x').html(msg.ok.pos.point.x);
  $('#y').html(msg.ok.pos.point.y);

  drawStep(
    msg.ok.pos.point.x,
    msg.ok.pos.point.y,
    msg.ok.pos.theta,
    msg.ok.cycle,
    msg.ok.phase
  );
}

function drawStep (x, y, theta, cycle, phase) {
  if (phase === 'charge') {
    // hack (getMission() dont send x,y if phase is diferent as run)
    x = 0;
    y = 0;
    theta = 180;
  }
  
  //offset is from the middle of the canvas
  var xoff = (pathLayer.width/2+xOffset);
  var yoff = (pathLayer.height/2+yOffset);
  x = parseInt(x, 10);
  y = parseInt(y, 10);
  var oldX = x;

  //x and y are reversed in pose... so rotate
  x = y;
  y = oldX;
  x+=xoff;
  y+=yoff;
  
  console.log('x: %d, y:%d, xoff: %d, yoff: %d', x, y, xoff, yoff);
  
  drawRobotBody(x, y, theta);
  //draw charging base
  drawDock();

  // draw changes in status with text.
  if (phase !== lastPhase) {
    textLayerContext.font = 'normal 12pt Calibri';
    textLayerContext.fillStyle = 'blue';
    textLayerContext.fillText(phase, x, y);
    getMapOutline();
    lastPhase = phase;
  } else {
    pathLayerContext.lineTo(x, y);
    pathLayerContext.stroke();
  }
}

function drawDock () {
  drawRotatedImage(robotBodyLayerContext, Dockimg, (pathLayer.width/2+xOffset), (pathLayer.height/2+yOffset), roombaangle-rotation);
}

function drawRobotBody (x, y, theta) {
  theta = parseInt(theta, 10);
  //var radio = 15; //roomba radius
  clearContext(robotBodyLayerContext);
  theta = (theta -90 + roombaangle);
  drawRotatedImage(robotBodyLayerContext, Roombaimg, x-Roombaimg.naturalWidth/2, y-Roombaimg.naturalHeight/2, theta-rotation);
  /*
  robotBodyLayerContext.beginPath();
  robotBodyLayerContext.arc(x, y, radio, 0, 2 * Math.PI, false);
  robotBodyLayerContext.fillStyle = 'limegreen';
  robotBodyLayerContext.fill();
  robotBodyLayerContext.lineWidth = 3;
  robotBodyLayerContext.strokeStyle = '#003300';
  robotBodyLayerContext.stroke();
  
  theta = (theta + roombaangle)%360;

  var outerX = x + radio * Math.cos(theta * (Math.PI / 180));
  var outerY = y + radio * Math.sin(theta * (Math.PI / 180));

  robotBodyLayerContext.beginPath();
  robotBodyLayerContext.moveTo(x, y);
  robotBodyLayerContext.lineTo(outerX, outerY);
  robotBodyLayerContext.strokeStyle = 'red';
  robotBodyLayerContext.lineWidth = 3;
  robotBodyLayerContext.stroke();
  */
}

function clearMap () {
  lastPhase = '';
  clearContext(pathLayerContext);
  clearContext(robotBodyLayerContext);
  clearContext(textLayerContext);
  drawOutline();
  pathLayerContext.beginPath();
}
function clearContext (ctx) {
  console.log('clear context');
  //clear a bigger area than you think, as rotated canvasses
  //leave remains inn the corners
  ctx.clearRect(0,0,ctx.canvas.width*2,ctx.canvas.height*2);
}

function drawRotatedText(ctx, mytext, x, y, deg) {
 //javascript is such a pain...
 var txtHeight = ctx.measureText(mytext).fontBoundingBoxAscent;
 ctx.textAlign = "center";
 if (deg == 0) {
   ctx.fillText(mytext, x, y+txtHeight);
 } else {
   ctx.save();
   ctx.translate(x, y);
   ctx.rotate(deg*Math.PI/180);
   ctx.fillText(mytext, 0, txtHeight);
   ctx.restore();
 }
}

function drawRotatedImage(ctx, img, x, y, deg) {
 //javascript is such a pain...
 if (deg == 0) {
   ctx.drawImage(img, x-img.naturalWidth/2, y-img.naturalHeight/2);
 } else {
   ctx.save();
   ctx.translate(x+img.naturalWidth/2, y+img.naturalHeight/2);
   ctx.rotate(deg*Math.PI/180);
   ctx.drawImage(img, -img.naturalWidth/2, -img.naturalHeight/2);
   ctx.restore();
 }
}

function drawOutline () {
  //draws the rectangular bounds of the map
  console.log('DrawOutline sizeX: %d, sizeY: %d, gXoff: %d, gYoff: %d', sizeX, sizeY, gXoff, gYoff);
  textLayerContext.beginPath();
  textLayerContext.lineWidth = 5;
  textLayerContext.strokeStyle="#FF0000";
  textLayerContext.strokeRect(gXoff, gYoff, sizeX, sizeY);//for white background
  textLayerContext.font = 'bold 40pt Calibri';
  textLayerContext.fillStyle = 'red';
  drawRotatedText(textLayerContext, '- W(x) +', textLayer.width/2, gYoff, 0);
  drawRotatedText(textLayerContext, '+ H(y) -', gXoff, textLayer.height/2, -90);
  textLayerContext.stroke();
  getMapOutline();
  drawDock();
}

function toggleMapping () {
  mapping = !mapping;
  if (mapping) startMissionLoop();
}

function getValue (name, actual) {
  var newValue = parseInt($(name).val(), 10);
  if (isNaN(newValue)) {
    alert('Invalid ' + name);
    $(name).val(actual);
    return actual;
  }
  return newValue;
}

function downloadCanvas () {
  var bodyCanvas = document.getElementById('robot_body_layer');
  var pathCanvas = document.getElementById('path_layer');

  var bodyContext = bodyCanvas.getContext('2d');
  bodyContext.drawImage(pathCanvas, 0, 0);

  document.getElementById('download').href = bodyCanvas.toDataURL();
  document.getElementById('download').download = 'current_map.png';
}

function shiftCanvas (ctx, x, y) {
  console.log('shifting: x: %f, y: %f', x, y);
  var imageData = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
  clearContext(ctx);
  ctx.putImageData(imageData, x, y);
}

function resizeCanvas(ctx, w, h) {
  rotateCanvas(ctx, 0); //rotate to 0 as changing the size of a canvas clears it
  var imageData = ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height);
  ctx.canvas.width = w;   //this will clear the canvas and set rotation to 0
  ctx.canvas.height = h;
  ctx.putImageData(imageData,0,0);
  //rotation = 0;  //note rotation is now 0
}

function rotateCanvas (ctx, absrot){
  rotation = rotation || 0;
  var rotdeg = (absrot-rotation);
  console.log('Abs Angle: %d, Rotate: %d deg', absrot, rotdeg);
  var radians=(rotdeg*Math.PI)/180;
  var absradians=(absrot*Math.PI)/180;
  // Create an second in-memory canvas:
  var mCanvas=document.createElement('canvas');
  mCanvas.width=ctx.canvas.width;
  mCanvas.height=ctx.canvas.height;
  var mctx=mCanvas.getContext('2d');
  //unrotate the image
  mctx.translate(mctx.canvas.width/2,mctx.canvas.height/2);
  mctx.rotate(radians-absradians);
  mctx.translate(-mctx.canvas.width/2,-mctx.canvas.height/2);
  // Draw your canvas onto the second canvas
  mctx.drawImage(ctx.canvas,0,0);
  //clear original canvas
  clearContext(ctx);
  //set rotation of canvas
  ctx.translate(ctx.canvas.width/2,ctx.canvas.height/2);
  ctx.rotate(radians);  //note, this is cumulative
  ctx.translate(-ctx.canvas.width/2,-ctx.canvas.height/2);
  //Draw the second canvas back to the (now rotated) main canvas:
  ctx.drawImage(mCanvas, 0, 0);
}

function UpdateCanvas () {
  var w = getValue('#sizew', sizeX);
  var h = getValue('#sizeh', sizeY);
  var newXOffset = getValue('#offsetx', xOffset);
  var newYOffset = getValue('#offsety', yOffset);
  var newRotation = getValue('#rotation', rotation);
  roombaangle = getValue('#roombaangle', roombaangle);
  var newmaxHeight = getValue('#maxheight', maxHeight);
  var x;
  var y;
  var deg;

  if (sizeX !== w) {
    console.log('redrawing x');
    if (sizeX == maxDim) {
      pathLayerContext.beginPath();
      resizeCanvas(pathLayerContext, w, w);
      robotBodyLayer.width = w;
      textLayer.width = w;
      robotBodyLayer.height = w;
      textLayer.height = w;
      newXOffset = xOffset+(sizeX-w)/2;
      rotation = 0; //resizing a canvas sets rotation to 0
    }
    sizeX = w;
  }

  if (sizeY !== h) {
    console.log('redrawing y');
    if (sizeY == maxDim) {
      resizeCanvas(pathLayerContext, h, h);
      robotBodyLayer.width = h;
      textLayer.width = h;
      robotBodyLayer.height = h;
      textLayer.height = h;
      newYOffset = yOffset+(sizeY-h)/2;
      rotation = 0; //resizing a canvas sets rotation to 0
    }
    sizeY = h;
  }

  if (newXOffset !== xOffset) {
    pathLayerContext.beginPath();
    deg = rotation*Math.PI/180;
    x = Math.round(Math.cos(deg) * (newXOffset - xOffset));
    y = Math.round(Math.sin(deg) * (newXOffset - xOffset));
    shiftCanvas(pathLayerContext, x, y);
    xOffset = newXOffset;
  }
  
  if (newYOffset !== yOffset) {
    pathLayerContext.beginPath();
    deg = rotation*Math.PI/180;
    x = Math.round(Math.cos(deg) * (newYOffset - yOffset));
    y = Math.round(Math.sin(deg) * (newYOffset - yOffset));
    shiftCanvas(pathLayerContext, x, y);
    yOffset = newYOffset;
  }
  
  if (newRotation !== rotation) {
    pathLayerContext.beginPath();
    rotateCanvas(pathLayerContext, newRotation);
    rotateCanvas(textLayerContext, newRotation);
    rotateCanvas(robotBodyLayerContext, newRotation);
    rotation = newRotation;
  }
  
  if (newmaxHeight != maxHeight) {
    console.log('new max-height: %s', newmaxHeight);
    canvasStyle.maxHeight = `${newmaxHeight}vh`;
    maxHeight = newmaxHeight
    console.log('set new max-height: %s', maxHeight);
  }   
      
  UpdateLineWidth();
  getDimentions();
  Updatevalues();
  clearContext(textLayerContext);
  clearContext(robotBodyLayerContext);
  drawOutline();
  console.log('updated canvas')
}

function saveValues () {
  var values = `mapsize = '(${$('#sizew').val()},
                            ${$('#sizeh').val()},
                            ${$('#offsetx').val()},
                            ${$('#offsety').val()},
                            ${$('#rotation').val()},
                            ${$('#roombaangle').val()})'`;
  $.post('/map/values', values, function (data) {
    $('#apiresponse').html(data);
  });
}

$('.metrics').on('change', function () {
  UpdateCanvas();
});

$('.action').on('click', function () {
  var me = $(this);
  var path = me.data('action');
  me.button('loading');
  $.get(path, function (data) {
    me.button('reset');
    $('#apiresponse').html(JSON.stringify(data));
  });
});

function resetMaxHeight () {
  $('#maxheight').val(orgMaxheight);
  UpdateCanvas();
}

$('#updateevery').on('change', function () {
  updateEvery = getValue('#updateevery', updateEvery);
});

$('#linewidth').on('change', function () {
  UpdateLineWidth();
});
