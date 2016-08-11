/**
 * Copyright 2016 Google, Inc
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
window.annotate = (function() {
  'use strict';
  function surround(text, tag, start, end, attrs) {
    var openingTag = '<' + tag + (
        attrs && attrs.length ? ' ' + attrs.join(' ') + '>' : '>');
    var closingTag = '</' + tag + '>';
    return text.substring(0, start) + openingTag + text.substring(start, end) +
        closingTag + text.substring(end);
  }

  function addSpans(text, tokens) {
    for (var i=tokens.length - 1; i >= 0; i--) {
      var token = tokens[i];
      // For some reason, " is depicted as ''
      if (token.partOfSpeech && token.partOfSpeech.tag == 'PUNCT') continue;
      var tokText = token.text;
      tokText.beginOffset = tokText.beginOffset || 0;
      var tokInText = text.substring(tokText.beginOffset, tokText.beginOffset + tokText.content.length);
      // TODO: what happens for nested entities??
      if (false && tokInText !== tokText.content) {
        var message = 'Misalignment of text at position ' + tokText.beginOffset + ': expected (' +
            tokText.content + ') but got (' + tokInText + ')';
        console.error(message);
        throw message;
      }

      var classes = ['token'];
      if ('entityIndex' in token) {
        classes.push('entity'+token.entityIndex);
      }
      var attrs = [
        'id=token' + i,
        'data-index=' + i,
        'class="' + classes.join(' ') + '"'];

      text = surround(text, 'span', tokText.beginOffset, tokText.beginOffset + tokText.content.length, attrs);

    }

    return text;
  }

  function labelPartOfSpeech(elem, partOfSpeech) {
    $('<div />').addClass('part-of-speech').appendTo(elem).text(partOfSpeech.tag);
  }

  function drawLine(from, to, label) {
    var STROKE_WIDTH = 10;
    var PADDING = 10;
    var fromPos = from.getBoundingClientRect();
    var toPos = to.getBoundingClientRect();
    var dx = (toPos.left + toPos.width/2) - (fromPos.left + fromPos.width/2),
        dy = (toPos.top + toPos.height/2) - (fromPos.top + fromPos.height/2);
    var svgPos = {
      width: 2*PADDING + (Math.abs(dx) || STROKE_WIDTH),
      height: 2*PADDING + (Math.abs(dy) || STROKE_WIDTH),
      top: dy < 0 ? (fromPos.height/2) + (dy - PADDING) : fromPos.height/2 - PADDING,
      left: dx < 0 ? (fromPos.width/2) + (dx - PADDING) : fromPos.width/2 - PADDING
    };
    for (var i in svgPos) {
      svgPos[i] = svgPos[i] + 'px';
    }

    var d3lines = d3.select(from).append('svg:svg').style(svgPos)
        .selectAll('line').data([{
          dx: dx,
          dy: dy
        }]);
    d3lines.enter().append('svg:line').attr({
          'stroke-width': STROKE_WIDTH,
          x1: dx < 0 ? -dx + PADDING : 0 + PADDING,
          x2: dx < 0 ? 0 + PADDING : dx + PADDING,
          y1: dy < 0 ? -dy + PADDING : 0 + PADDING,
          y2: dy < 0 ? 0 + PADDING : dy + PADDING
        });
    d3lines.exit().remove();

    //$(to).css({outline: '1px solid rgba(255,0,0,1)'});
  }

  function drawDep(e) {
    var elem = $(e.currentTarget);
    var parent = elem.closest('#article-content');
    // TODO: object model?
    var token = elem.data('token');
    labelPartOfSpeech(elem, token.partOfSpeech);
    drawLine(
        elem[0],
        parent.find('#token' + token.dependencyEdge.headTokenIndex)[0],
        token.dependencyEdge.label
        );
  }

  function hideDep(e) {
    var elem = $(e.currentTarget);
    elem.children().remove();
  }

  function annotateTokens(text, tokens) {
    text = addSpans(text, tokens);
    $('#article-content')
        .html(text)
        .on('mouseover', '.token', drawDep)
        .on('mouseout', '.token', hideDep);
  }

  function highlightAll(e) {
    var elem = $(e.currentTarget);
    var parent = elem.closest('#article-content');
    // TODO: object model?
    var token = elem.data('token');

    parent.addClass('highlighting')
        .find('.entity' + token.entityIndex).addClass('highlight');
  }

  function unhighlightAll(e) {
    $('#article-content').removeClass('highlighting')
        .find('.highlight').removeClass('highlight');
  }

  function showLoader(promise) {
    var overlay = $('#overlay');
    var greyScreen = overlay.add('.grey-screen').fadeIn();
    var elements = overlay
        .children(':visible')
        .not('.mdl-spinner')
        .not('.grey-screen')
        .css('z-index', 1);

    overlay.find('.mdl-spinner').fadeIn();
    promise.always(function() {
      overlay.find('.mdl-spinner').fadeOut();
      elements.css('z-index', '').hide();
    }).fail(function(jqXhr) {
      $('#snackbar')[0].MaterialSnackbar.showSnackbar({
        message: 'There was an error: ' + (
            jqXhr.responseJSON && jqXhr.responseJSON.error)
      });
      overlay.fadeOut();
      console.log(arguments);
    });
    return overlay;
  }

  function showEntityGraph(e) {
    var elem = $(e.currentTarget);
    var token = elem.data('token');

    var params = {
      type: token.type,
      limit: 10,
      page: 0
    };
    if (token.metadata && token.metadata.wikipedia_url) {
      params.wiki = token.metadata.wikipedia_url;
    } else {
      params.name = token.name;
    }
    var promise = $.get('/common_entities', params);
    var container = showLoader(promise);
    promise.then(function(result) {
      createGraph(result.rows, token, elem, container.find('.entity-graph')[0]);
    });
  }

  var WP_URL = 'http://en.wikipedia.org/?curid=';
  function showPagesForPair(token) {
    return function(datum) {
      var params = {
        name2: datum.f[0].v
      };
      if (token.metadata && token.metadata.wikipedia_url) {
        params.wiki1 = token.metadata.wikipedia_url;
      } else {
        params.name1 = token.name;
      }
      var promise = $.get('/pages_with_both', params);
      promise.then(function(result) {
        var container = $('#page-list');
        container.find('.subtitle').text(
            'Pages that contain both entities ' +
            token.name + ' and ' + params.name2);

        var pageSize = 50;
        function loadPage(e) {
          var target = $(e.currentTarget),
              container = $(e.delegateTarget);
          var n = container.data('pageNumber');
          if (target.text() === 'chevron_left') {
            n -= 1;
            container.scrollTop(container[0].scrollHeight);
          } else if (target.text() === 'chevron_right') {
            n += 1;
            container.scrollTop(0);
          }
          container.data('pageNumber', n);

          var list = result.rows.slice(n * pageSize, (n+1) * pageSize);
          var items = list.map(function(v) {
            return $('<li class="mdl-list__item" />').html($('<a />').attr({
              class: 'dotted',
              //href: WP_URL + v.f[1].v
              href: '/?wiki_title=' + encodeURIComponent(v.f[0].v)
            }).text(v.f[0].v));
          });

          var controls = $('<li class="mdl-list__item" />');
          items.push(controls);
          if (n > 0) {
            controls.append($('<button />').attr({
              class: 'mdl-button mdl-button--icon ' +
                      'mdl-js-button mdl-js-ripple-effect'
            }).html('<i class="material-icons">chevron_left</i>'));
          }
          if ((n + 1) * pageSize < result.rows.length) {
            controls.append($('<button />').attr({
              class: 'mdl-button mdl-button--icon ' +
                      'mdl-js-button mdl-js-ripple-effect'
            }).html('<i class="material-icons">chevron_right</i>'));
          }
          container.find('.page-list').html(items);
        }

        if (undefined == container.data('pageNumber')) {
          // Load the event handler
          container.on('click', 'button', loadPage);
        }
        container.data('pageNumber', 0);
        loadPage({delegateTarget: container});
        container.fadeIn();
      });

      showLoader(promise);
    };
  }

  function createGraph(rows, token, elem, container) {
    container = container || $('body')[0];
    var contentDims = document.getElementById(
        'article-content').getBoundingClientRect();
    $(container).fadeIn(100);

    var minDistance = 100, range = 100;
    var width = contentDims.width,
        height = Math.min(2.3 * (minDistance + range), $(window).height());

    var total = 0, min = 9e7, max = 0;

    rows.forEach(function(row) {
        var name = row.f[0].v;
        var count = parseInt(row.f[1].v, 10);
        console.log(name, count);

        if (count < min) min = count;
        if (count > max) max = count;
      });
    if (max == min) { max = min + 1; }

    var force = d3.layout.force()
        .linkDistance(function(d) {
          return minDistance + range * (1 - (d.value - min) / (max - min));
        })
        .size([width, height]);

    var svg = d3.select(container).selectAll('svg')
        .data([token]);
    svg.enter()
        .append('svg')
        .attr({
          width: width,
          height: height,
          class: 'graph'
        });
    svg.exit().remove();

    // Fade it in now, so we can get the text widths
    $(svg[0]).fadeIn();

    var links = rows.map(
        function(row, i) {
          return {
            source: i+1,
            target: 0,
            value: parseInt(row.f[1].v, 10)
          };
        });
    var nodes = [{
      f:[{v:token.name}, {v:0}]
    }].concat(rows);

    var delta = 2 * Math.PI / nodes.length,
        center = {x: width/2, y: minDistance + range};
    nodes.forEach(function(d, i) {
      if (i === 0) {
        d.x = center.x;
        d.y = center.y;
      } else {
        var angle = delta * i;
        d.x = center.x + Math.cos(angle) * width / 4;
        d.y = center.y + Math.sin(angle) * height / 4;
      }
    });
    force
        .nodes(nodes)
        .links(links)
        .gravity(0.1)
        .linkStrength(.1)
        .friction(0.9)
        .charge(-530)
        .theta(0.8)
        .alpha(0.1)
        .start();

    var link = svg.selectAll('.link')
        .data(links);
    link.enter().insert('line', ':first-child')
        .attr('class', 'link')
        .style('stroke-width', 3);
    link.exit().remove();

    var node = svg.selectAll('.node')
        .data(nodes);
    var gEnter = node.enter()
        .append('g')
        .attr({
          class: 'node',
          transform: 'translate(1, 1)'
        })
        .call(force.drag);
    // Add ellipses
    gEnter.append('ellipse')
        .style({
          stroke: '#aa0000',
          fill: '#ffffff'
        });
    // Add text labels
    gEnter.append('text')
        .attr({
          dy: '.3em'
        }).on('click', showPagesForPair(token))
        .style('text-anchor', 'middle');

    node.exit().remove();

    node.select('text')
        .text(function(d) {
          var v = d.f[0].v;
          if (v.length > 25) {
            return v.substring(0, 22) + '...';
          } else {
            return v;
          }
          // calculate the width of the texts
        }).each(function(d) {
          d.textWidth = this.getComputedTextLength();
        });

    node.select('ellipse').attr({
          rx: function(d) { return Math.min(200, 10 + d.textWidth / 2); },
          ry: function(d) { return Math.min(50, Math.max(15, d.textWidth / 3)); }
        })

    force.on('tick', function() {
      link.attr('x1', function(d) { return d.source.x; })
          .attr('y1', function(d) { return d.source.y; })
          .attr('x2', function(d) { return d.target.x; })
          .attr('y2', function(d) { return d.target.y; });

      node.attr("transform", function(d) {
        return 'translate(' + d.x + ',' + d.y + ')';
      })
    });
  }

  function annotateEntities(text, entities, entityType) {
    entities.forEach(function(v, i) {
      v.entityIndex = i;
    });

    // Create a list of entities sorted by their salience
    var sortedEntities = entities.slice();
    sortedEntities.sort(function(e1, e2) {
      return e2.salience - e1.salience;
    });
    $('#article-content .top10 ul').html(
        sortedEntities.slice(0, 10).map(function(entity) {
          var li = $('<li/>');

          var token = $('<span/>').attr({
            class: 'token entity' + entity.entityIndex
          }).text(entity.name);
          token.data('token', entity);

          switch(entity.type) {
            case 'PERSON':
              li.append('<i class="material-icons">face</i>');
              break;
            case 'LOCATION':
              li.append('<i class="material-icons">place</i>');
              break;
            case 'ORGANIZATION':
              li.append('<i class="material-icons">business</i>');
              break;
            case 'EVENT':
              li.append('<i class="material-icons">event</i>');
              break;
            case 'WORK_OF_ART':
              li.append('<i class="material-icons">color_lens</i>');
              break;
            case 'CONSUMER_GOOD':
              li.append('<i class="material-icons">kitchen</i>');
              break;
            case 'OTHER':
              li.append('<i class="material-icons">texture</i>');
              break;
            case 'UNKNOWN':
              li.append('<i class="material-icons">crop_square</i>');
              break;
          }

          li.append(token);

          li.append($('<span/>').text(': ' + entity.salience));

          return li;
        }));


    var tokens = [];
    for(var i=0,len=entities.length; i<len; i++) {
      var entity = entities[i];
      for(var j=0,jlen=entity.mentions.length; j<jlen; j++) {
        if(!entity.mentions[j].text.beginOffset) {
          entity.mentions[j].text.beginOffset = 0;
        }
        if (!entityType || entityType === entity.type) {
          tokens.push($.extend({}, entity, entity.mentions[j]));
        }
      }
    }
    tokens.sort(function(a, b) {
      return a.text.beginOffset - b.text.beginOffset;
    });

    var elem = $('<div />').html(addSpans(text, tokens));
    elem.find('.token').each(function(i, el) {
      var elem = $(el);
      elem.data('token', tokens[elem.data('index')]);
    });
    $('#article-content .body-text')
        .html(elem);
    $('#article-content')
        .off('.annotateEntities')
        .on('mouseover.annotateEntities', '.token', highlightAll)
        .on('mouseout.annotateEntities', '.token', unhighlightAll)
        .on('click.annotateEntities', '.token', showEntityGraph);

    // Show a brief visualization to highlight all entities
    if (isFirstTime()) {
      // Do this asyncronously in case the layout shifts during render.
      setTimeout(function() {
        showInstructions($('.body-text .token'));
      }, 10);
    }
  }

  function getParam(key) {
    var re = new RegExp('(^|;|&|\\?)\\s*' + key + '\\s*=([^;]+)');
    var placesToSearch = [location.search.substring(1), document.cookie];
    for (var i=0, len=placesToSearch.length; i<len; i++) {
      var params = placesToSearch[i];
      var result = re.exec(params);
      if (result && result.length >= 2) {
        return result[2];
      }
    }
  }
  function isFirstTime() {
    var firstTime = getParam('firstTime');
    return firstTime !== 'false';
  }
  function setFirstTime(bool) {
    document.cookie = 'firstTime=' + (bool ? 'true' : 'false');
  }
  function getViewportDimensions() {
    return {
      width: $(window).width(),
      height: $(window).height()
    };
  }

  // converts bottom/right to the css definition
  function convertBottomRight(clientRect) {
    var viewport = getViewportDimensions();
    return $.extend({}, clientRect, {
      bottom: viewport.height - (clientRect.top + clientRect.height),
      right: viewport.width - (clientRect.left + clientRect.width)
    });
  }

  // Position the overlay around the given element
  function positionShowcase(target) {
    var showcase = $('#showcase');
    if (target.currentTarget) {
      // Called as an event handler
      target = showcase.data('target');

      // If the showcase is done, remove the event handler
      if (!showcase.is(':visible')) {
        $(window).off('.showcase');
        return;
      }
    } else if (!showcase.data('target')) {
      // This is the first time we've been positioned. Add an event listener.
      $(window).on('resize.showcase scroll.showcase', positionShowcase);
    }
    showcase.data('target', target);

    var bounds = convertBottomRight(target[0].getBoundingClientRect());
    var viewport = getViewportDimensions();

    // Add some padding around the highlighted rectangle
    var padding = {w: 8, h: 4};
    bounds = {
      top: bounds.top - padding.h,
      left: bounds.left - padding.w,
      bottom: bounds.bottom - padding.h,
      right: bounds.right - padding.w,
      width: bounds.width + 2*padding.w,
      height: bounds.height + 2*padding.h
    };
    var borderWidth = 2 * Math.max(
        bounds.top, bounds.left, bounds.bottom, bounds.right);
    var radius = Math.max(bounds.width, bounds.height);

    var overlay = $('#showcase .showcase-overlay').css({
      top: (bounds.top + (bounds.height / 2)) - (borderWidth + (radius / 2)),
      left: (bounds.left + (bounds.width / 2)) - (borderWidth + (radius / 2)),
      borderWidth: borderWidth,
      width: radius,
      height: radius
    });
    return showcase;
  }

  function positionInstructions(instructions, target) {
    var showcase = $('#showcase');
    // Position the overlay around the given entity
    if (instructions.currentTarget) {
      if (!showcase.is(':visible')) {
        // The showcase is done. Remove the event handlers
        $(window).off('.instructions');
        return;
      }

      // Called as an event handler
      instructions = showcase.data('instructions');
      target = showcase.data('target');
    } else if (!showcase.data('instructions')) {
      // This is the first time we've been positioned. Add an event listener.
      $(window).on(
          'resize.instructions scroll.instructions', positionInstructions);
    }
    showcase.data('instructions', instructions);

    if (instructions.is(':visible')) {
      var instructionBounds = convertBottomRight(
          instructions[0].getBoundingClientRect());
    } else {
      instructions.show();
      var instructionBounds = convertBottomRight(
          instructions[0].getBoundingClientRect());
      instructions.hide();
    }

    var targetBounds = convertBottomRight(target[0].getBoundingClientRect());
    var radius = Math.max(targetBounds.width, targetBounds.height) / 2;

    var viewport = getViewportDimensions();

    if (targetBounds.top - radius > instructionBounds.height) {
      // position the instructions above
      instructions.css({
        top: '',
        bottom: targetBounds.bottom + radius + 50
      });
    } else {
      instructions.css({
        bottom: '',
        top: targetBounds.top + radius + 50
      });
    }

    return instructions;
  }

  function showInstructions(samples) {
    var bounds = convertBottomRight(samples[0].getBoundingClientRect());
    var showcase = positionShowcase(samples.eq(0));

    showcase.fadeIn(200, function() {
      positionInstructions(text.children('.step').eq(0), samples.eq(0))
          .fadeIn(200);
    });

    // Display the instructions
    var text = showcase.find('.showcase-text');
    text.on('click', 'button', function showNextStep(e) {
      var thisStep = $(e.currentTarget).closest('.step');
      thisStep.fadeOut(200, function() {
        var nextStep = thisStep.next();
        if (!nextStep.length) {
          showcase.fadeOut(100);
          setFirstTime(false);
          return;
        }
        nextStep.fadeIn(200);
        var sample = samples.eq(nextStep.index());
        positionShowcase(sample);
        positionInstructions(nextStep, sample);
      });
    });

    /*
    $('#article-content').addClass('highlighting')
        .find('.token').addClass('highlight');
    setTimeout(unhighlightAll, 1000);
    */
  }

  function showSentiment(sentiment) {
    var svg = d3.select('.sentiment svg').data([sentiment.polarity]);
    var width = parseInt($('.sentiment svg').attr('width')) - 10;
    var scale = d3.scale.linear()
        .domain([-1, 1])
        .range([0, width])
        .interpolate(d3.interpolateRound);
    var axis = d3.svg.axis()
        .scale(scale)
        .orient('bottom')
        .ticks(5)
        .tickSize(3);
    var svgAxis = svg.select('.axis');
    svgAxis.call(axis)
        .append('text')
        .style('text-anchor', 'middle')
        .style('text-transform', 'uppercase')
        .text(function(d) { return d.key; });;
    var triangle = {w:5, h:9};
    var svgPointer = svgAxis
        .selectAll('polygon.triangle')
        .data([sentiment.polarity]);
    svgPointer.enter().append('polygon');
    svgPointer.attr({
          class: 'triangle',
          transform: function(d) {
            return 'translate(' + (scale(d) - .5 * triangle.w) + ',-14)';
          },
          points: [[triangle.w/2, triangle.h], [triangle.w, 0], [0, 0]]
              .map(function(pair) { return pair.join(','); }).join(' ')
        });
    svgPointer.exit().remove();
  }
  function closeOverlay(e) {
    var overlay = $('#overlay');
    overlay.add(overlay.children()).fadeOut();
  }

  return function(analysis) {
    //annotateTokens(analysis.content, analysis.tokens);
    showSentiment(analysis.documentSentiment);
    annotateEntities(analysis.content, analysis.entities);//, 'PERSON');
    // Hide all the overlays when the grey screen is clicked
    $(document).on('click', '.grey-screen', closeOverlay)
        .on('click', '.mdl-card__menu button', closeOverlay);
        /*
        .on('click', 'svg.graph', function(e) {
          if ($(e.target).is('.graph')) {
            closeOverlay(e);
          }
        });
        */
  };
})();
