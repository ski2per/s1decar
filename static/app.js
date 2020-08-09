/*
var ETCD_API = "http://etcd.cetcxl.com:2379/v2/keys"
var ROUTER_COLOR = "#00FF00"
var network, nodes, edges, subnets
var nodesArray = []
var edgesArray = []
var router_nodes = []
var node_nodes = []
var orgs = []

function main() {
  axios.defaults.headers.common['Authorization'] = `Basic ${btoa("anon:P@ssw0rd")}`
  // First, retrieve info unser /coreos.com/network/subnets and /coreos.com/network/routes
  Promise.all([
    axios.get(`${ETCD_API}/coreos.com/network/subnets`),
    axios.get(`${ETCD_API}/coreos.com/network/routes`),
  ])
  .then(function (response) {
    subnets = response[0].data.node.nodes

    generateNodesArray(subnets)
    drawNode()

    let org_keys = response[1].data.node.nodes
    // Then retrieve all info under /coreos.com/network/routes/*
    org_keys.forEach((element) => {
      axios.get(`${ETCD_API}/${element.key}`)
      .then(function(response){
        response.data.node.nodes.forEach((item) => {
          ip = extractIP(item.key)
          type = JSON.parse(item.value).node_type

          if (type == "router") {
            styleRouterNode(ip)
          }
          orgs.push(item)
        })
      })
      .catch(function(error){
        console.log(error)
        console.log(`Error processing ${element.key}`)
      })
    })


    // generateEdges(orgs)
    // styleRouterNode()

  }).catch(function(error){
    console.log(error)
    console.log("Error loading data from Etcd")
  })
}

function generateNodesArray(subnets) {

  // Process subnets(sn) to generate nodes
  // node format:
  // {
  //   id: 1,
  //   label: "name"
  // }

  subnets.forEach((element, index) => {
    extractIP(element.key)
    ip = extractIP(element.key)
    // console.log(ip)
    nodesArray.push({id: index+1, label: ip})
  })
}

function extractIP(text) {
  // "/coreos.com/network/subnets/10.14.192.0-20"     -> 10.14.192.0
  // "/coreos.com/network/routes/telecom/10.15.224.0" -> 10.15.224.0
  if (text.includes("-")) {
    let tmp = text.split("-")[0]
    return tmp.split("/").pop()
  } else {
    return text.split("/").pop()
  }

}

function styleRouterNode(router) {
  nodesArray.forEach((item, index) => {
    if (item.label == router) {
      router_nodes.push(item)

      item["color"] = ROUTER_COLOR
      item["group"] = 6
      nodesArray.splice(index, 1, item)
      nodes.update([item])
    } else {
      node_nodes.push(item)
    }

  })
}

function drawNode() {
  nodes = new vis.DataSet(nodesArray)
  edges = new vis.DataSet([
  // {from: 1, to: 3},
  // {from: 1, to: 2},
  // {from: 2, to: 4},
  // {from: 2, to: 5},
  ]);

  var container = document.getElementById('mynetwork');
  var data = {
    nodes: nodes,
    edges: edges
  };

  var options = {
    nodes: {
      shape: "dot",
      size: 15
    }
  }

  network = new vis.Network(container, data, options)
}
*/

function main() {
    var currentURL = window.location.href
    Promise.all([
        axios.get(`${currentURL}topo`),
    ])
    .then(function(response){
        nodes = new vis.DataSet(response[0].data.nodes)
        edges = new vis.DataSet(response[0].data.edges)
        var info = response[0].data.info

        var container = document.getElementById('topo');
        var info_element = document.getElementById('info')
        var data = {
            nodes: nodes,
            edges: edges
        };

        var options = {
            physics: true,
            nodes: {
                shape: "dot",
                size: 15,
                borderWidth: 2,
                color: {
                    background: "#FFFFFF"
                }
            },
        }

        network = new vis.Network(container, data, options)
        info_element.innerHTML = `
        <div>
            <p class="total">Total nodes - ${info.total}</p>
            <p>[router]: <b>${info.router}</b></p>
            <p>[node]: <b>${info.node}</b></p>
            <p>[internal]: <b>${info.internal}</b></p>
        </div>
        `
//        info.forEach((ele) => {
//            console.log(ele)
//        })
    })
    .catch(function(error){
    console.log(error)
    console.log("Error loading data from Etcd")
  })
}
main()

