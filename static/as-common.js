// various JS utilities shared by all templates

// helper function so that we can access keys in url bar
let QueryString = function () {
  // This function is anonymous, is executed immediately and 
  // the return value is assigned to QueryString!
  let query_string = {};
  let query = window.location.search.substring(1);
  let vars = query.split("&");
  for (let i=0;i<vars.length;i++) {
    let pair = vars[i].split("=");
        // If first entry with this name
    if (typeof query_string[pair[0]] === "undefined") {
      query_string[pair[0]] = decodeURIComponent(pair[1]);
        // If second entry with this name
    } else if (typeof query_string[pair[0]] === "string") {
      let arr = [ query_string[pair[0]],decodeURIComponent(pair[1]) ];
      query_string[pair[0]] = arr;
        // If third or later entry with this name
    } else {
      query_string[pair[0]].push(decodeURIComponent(pair[1]));
    }
  }
    return query_string;
}();

function jq( myid ) { return myid.replace( /(:|\.|\[|\]|,)/g, "\\$1" ); } // for dealing with ids that have . in them

function buildAuthorsHtml(authors) {
  let res = '';
  for(let i=0,n=authors.length;i<n;i++) {
    let link = '/search?q=' + authors[i].replace(/ /g, "+");
    res += '<a href="' + link + '">' + authors[i] + '</a>';
    if(i<n-1) res += ', ';
  }
  return res;
}

// populate papers into #rtable
// we have some global state here, which is gross and we should get rid of later.
let pointer_ix = 0; // points to next paper in line to be added to #rtable
let showed_end_msg = false;
function addPapers(num, dynamic) {
  if(papers.length === 0) { return true; } // nothing to display, and we're done

  let root = d3.select("#rtable");

  let base_ix = pointer_ix;
  for(let i=0;i<num;i++) {
    let ix = base_ix + i;
    if(ix >= papers.length) {
      if(!showed_end_msg) {
        if (ix >= numresults){
          let msg = 'Results complete.';
        } else {
          let msg = 'You hit the limit of number of papers to show in one result.';
        }
        root.append('div').classed('msg', true).html(msg);
        showed_end_msg = true;
      }
      break;
    }
    pointer_ix++;

    let p = papers[ix];
    let div = root.append('div').classed('apaper', true).attr('id', p.pid);

    let tdiv = div.append('div').classed('paperdesc', true);
    tdiv.append('span').classed('ts', true).append('a').attr('href', p.link).attr('target', '_blank').html(p.title);
    tdiv.append('br');
    tdiv.append('span').classed('as', true).html(buildAuthorsHtml(p.authors));
    tdiv.append('br');
    let cat_link = '/search?q=' + p.composed_conf_id;
    res = '<a href="' + cat_link + '">' + p.conf_name + '</a>';
    tdiv.append('span').classed('cs', true).html(res);
    tdiv.append('br');

    // action items for each paper
    let ldiv = div.append('div').classed('dllinks', true);
    ldiv.append('a').attr('href', p.pdf_link).attr('target', '_blank').html('pdf');
    

    // rank by tfidf similarity
    ldiv.append('br');
    let similar_span = ldiv.append('span').classed('sim', true).attr('id', 'sim'+p.pid).html('show similar');
    similar_span.on('click', function(pid){ // attach a click handler to redirect for similarity search
      return function() {
        let chosen_confs = accessCookie('confs');
        if (chosen_confs.length === 0) {
          chosen_confs = 'all';
        }
        window.location.replace('/' + pid + '?confs=' + chosen_confs);
      }
    }(p.pid)); // closer over the paper id

    ldiv.append('br');

    div.append('div').attr('style', 'clear:both');

    if(typeof p.abstract !== 'undefined') {
      let abdiv = div.append('span').classed('tt', true).html(p.abstract);
      if(dynamic) {
        MathJax.Hub.Queue(["Typeset",MathJax.Hub,abdiv[0]]); //typeset the added paper
      }
    }

    if(render_format == 'paper' && ix === 0) {
      let filter_div = div.append('div').classed('paperdivider', true);
      fillFilterDiv(filter_div, p);
      div.append('div').classed('paperdivider', true).html('Most similar papers:');
    }
  }

  return pointer_ix >= papers.length; // are we done?
}

// code gotten from: https://www.guru99.com/cookies-in-javascript-ultimate-guide.html
function accessCookie(cookieName) {
  let name = cookieName + "=";
  let allCookieArray = document.cookie.split(';');
  for(let i=0; i<allCookieArray.length; i++)
  {
    let temp = allCookieArray[i].trim();
    if (temp.indexOf(name)==0)
    return temp.substring(name.length,temp.length);
  }
  return "";
}

// code gotten from: https://www.guru99.com/cookies-in-javascript-ultimate-guide.html
function createCookie(cookieName, cookieValue, daysToExpire) {
  let date = new Date();
  date.setTime(date.getTime()+(daysToExpire*24*60*60*1000));
  document.cookie = cookieName + "=" + cookieValue + "; expires=" + date.toGMTString();
}

function fillFilterDiv(filter_div, paper) {
  // create a div with the options to filter the similar papers results
  let chosen_confs = QueryString.confs;

  // add a "Select all" checkbox
  let select_div = filter_div.append('div').attr('style', 'display: grid; grid-template-columns: 1fr 1fr');
  let select_cell_div = select_div.append('div').attr('style', 'text-align:center');
  let check = select_cell_div.append('input')
    .attr('id', 'allconf_all')
    .attr('type', 'checkbox')
    .attr('onClick', 'updateCheckBoxes("all")');
  if (chosen_confs === 'all') {
    check.property('checked', true);
  }
  select_cell_div.append('label').text(' Select all');

  // add a "Select none" checkbox
  select_cell_div = select_div.append('div').attr('style', 'text-align:center');
  check = select_cell_div.append('input')
    .attr('id', 'allconf_none')
    .attr('type', 'checkbox')
    .attr('onClick', 'updateCheckBoxes("none")');
  if (chosen_confs === 'none') {
    check.property('checked', true);
  }
  select_cell_div.append('label').text(' Select none');
  filter_div.append('hr');

  // add checkboxes to select by year
  let last_year = 2019;
  let max_years = 5;
  let col_width = '90px';
  let conf_div = filter_div.append('div').attr('style', 'display: flex');
  conf_div.append('div').attr('style', 'width: '+col_width);
  for (let j=0; j < max_years; j++) {
    let conf_year = last_year - j;
    conv_cell = conf_div.append('div').attr('style', 'text-align:center; width: '+col_width);
    check = conv_cell.append('input')
      .attr('id', 'yearconf_'+conf_year.toString())
      .attr('type', 'checkbox')
      .attr('onClick', 'updateCheckBoxes("'+conf_year+'")')
    if (chosen_confs === 'all') {
      check.property('checked', true);
    }
    conv_cell.append('label')
      .html(' ' + conf_year.toString());
  }
  filter_div.append('hr');
  // add checkboxes for each conference
  conf_div = filter_div.append('div').attr('style', 'display: flex');
  let conference_names = Object.keys(conferences);
  for (let i=0; i < conference_names.length; i++) {
    let conf_name = conference_names[i];
    let conference_years = conferences[conf_name][1];
    // add a checkbox with the conference name
    conf_div = filter_div.append('div').attr('style', 'display: flex');
    conv_cell = conf_div.append('div').attr('style', 'width: '+col_width+'; border-right: 1px solid gray');
    check = conv_cell.append('input')
      .attr('id', 'nameconf_'+conf_name.toLowerCase())
      .attr('type', 'checkbox')
      .attr('onClick', 'updateCheckBoxes("'+conf_name.toLowerCase()+'")')
    if (chosen_confs === 'all') {
      check.property('checked', true);
    }
    conv_cell.append('label')
      .html(' ' + conf_name);
    // add checkboxes with the available years of each conference
    for (let j=0; j < max_years; j++) {
      let conf_year = (last_year - j).toString();
      conv_cell = conf_div.append('div').attr('style', 'text-align:center; width: '+col_width);
      if (conference_years.includes(conf_year)) {
        check = conv_cell.append('input')
          .attr('id', 'conf_'+conf_name.toLowerCase()+conf_year)
          .attr('value', conf_name+conf_year)
          .attr('type', 'checkbox')
        if (chosen_confs === 'all' || chosen_confs.includes(conf_name+conf_year)) {
          check.property('checked', true);
        }
        conv_cell.append('label')
          .html(' ' + conf_year);
      }
    }
  }
  filter_div.append('hr');
  filter_div.append('input').attr('type', 'submit').attr('onClick', 'updateConfsFilter("'+paper.pid+'")').attr('value', 'Filter results');
}

function updateCheckBoxes(mode) {
  // update the checked status of the checkboxes used to filter the similar results
  if (mode === 'all') {
    // when clicking "Select all"
    d3.selectAll('input[id^=yearconf]').property('checked', true);
    d3.selectAll('input[id^=nameconf]').property('checked', true);
    d3.selectAll('input[id^=conf]').property('checked', true);
    d3.select('#allconf_all').property('checked', true);
    d3.select('#allconf_none').property('checked', false);
  } else if (mode === 'none') {
    // when clicking "Select none"
    d3.selectAll('input[id^=yearconf]').property('checked', false);
    d3.selectAll('input[id^=nameconf]').property('checked', false);
    d3.selectAll('input[id^=conf]').property('checked', false);
    d3.select('#allconf_all').property('checked', false);
    d3.select('#allconf_none').property('checked', true);
  } else if (isNaN(mode)) {
    // when clicking a conference name
    if (d3.select('#nameconf_'+mode).property('checked')) {
      d3.selectAll('input[id^=conf_'+mode+']').property('checked', true);
    } else {
      d3.selectAll('input[id^=conf_'+mode+']').property('checked', false);
    }
  } else {
    // when clicking an year
    mode = mode.toString();
    if (d3.select('#yearconf_'+mode).property('checked')) {
      d3.selectAll('input[id$="'+mode+'"]').property('checked', true);
    } else {
      d3.selectAll('input[id$="'+mode+'"]').property('checked', false);
    }
  }
}

function updateConfsFilter(pid) {
  // update the selection of conferences to filter the results of similar papers.
  // The checked checkboxes are used to build the url, and the page is refreshed
  let checked_confs = d3.selectAll('input[id^=conf]:checked');
  let filter_str = '';
  checked_confs.each(function()
  {
    filter_str += $(this).attr('value') + ',';
  });
  filter_str = filter_str.slice(0, -1);
  if (filter_str.length == 0) {
    filter_str = 'all';
  }
  window.location.replace('/' + pid + '?confs=' + filter_str);
  createCookie('confs', filter_str, 30);
}
