// when page loads...
$(document).ready(function(){

  urlq = QueryString.q;

  let conference_names = Object.keys(conferences);
  let chosen_conf = QueryString.conf;
  let chosen_year = QueryString.year;
  let chosen_type = QueryString.type;

  // display message, if any
  if(msg !== '') {
    d3.select("#rtable").append('div').classed('msg', true).html(msg);
  }

  // add papers to #rtable
  let done = addPapers(10, false);
  if(done) { $("#loadmorebtn").hide(); }

  // set up infinite scrolling for adding more papers
  $(window).on('scroll', function(){
    let scroll_top = $(document).scrollTop();
    let window_height = $(window).height();
    let body_height = $(document).height() - window_height;
    let scroll_percentage = (scroll_top / body_height);
    if(scroll_percentage > 0.9) {
      let done = addPapers(5, true);
      if(done) { $("#loadmorebtn").hide(); }
    }
  });

  // just in case scrolling is broken somehow, provide a button handler explicit
  $("#loadmorebtn").on('click', function(){
    let done = addPapers(5, true);
    if(done) { $("#loadmorebtn").hide(); }
  });

  if(papers.length === 0) { $("#loadmorebtn").hide(); }

  if(!(typeof urlq == 'undefined')) {
    d3.select("#qfield").attr('value', urlq.replace(/\+/g, " "));
  }

  let link_endpoint = '';

  // add conference links
  let elt = d3.select('#recommend-time-choice');
  for(let i=0; i<conference_names.length; i++) {
    let conf_name = conference_names[i];
    let url_text = '/'+link_endpoint+'?'+'conf='+conf_name+'&year='+conferences[conf_name][1][0];
    if (include_workshop_papers) {
      url_text = url_text+'&type='+conferences[conf_name][0][0];
    }
    let aelt = elt.append('a').attr('href', url_text);
    let delt = aelt.append('div').classed('timechoice', true).html(conf_name);
    if(typeof chosen_conf !== 'undefined' && chosen_conf === conf_name) { delt.classed('timechoice-selected', true); } // also render as chosen
  }
  if(typeof chosen_conf !== 'undefined') {
    let conference_years = conferences[chosen_conf][1];
    // add conference years links
    elt = d3.select('#conference-year');
    for(let i=0;i<conference_years.length;i++) {
      let year = conference_years[i];
      let url_text = '/'+link_endpoint+'?'+'conf='+chosen_conf+'&year='+year;
      if (include_workshop_papers) {
        url_text = url_text+'&type='+conferences[chosen_conf][0][0];
      }
      let aelt = elt.append('a').attr('href', url_text);
      let delt = aelt.append('div').classed('timechoice', true).html(year);
      if(typeof chosen_year !== 'undefined' && chosen_year === year) { delt.classed('timechoice-selected', true); } // also render as chosen
    }
    // add links to main and workshop papers
    if (include_workshop_papers && typeof chosen_year !== 'undefined') {
      let conference_types = conferences[chosen_conf][0];
      elt = d3.select('#conference-type');
      for(let i=0;i<conference_types.length;i++) {
        let ctype = conference_types[i];
        let aelt = elt.append('a').attr('href', '/'+link_endpoint+'?'+'conf='+chosen_conf+'&year='+chosen_year+'&type='+ctype);
        let delt = aelt.append('div').classed('timechoice', true).html(ctype);
        if(chosen_type === ctype) { delt.classed('timechoice-selected', true); } // also render as chosen
      }
    }
  }
});