# visualize_graph.py
from rdflib import Graph, URIRef, Literal, RDF, RDFS, Namespace
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
import random

TTL_FILE = Path("output/knowledge_graph.ttl")

SCHEMA = Namespace("https://schema.org/")
EX = Namespace("http://example.org/food/")
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")

class AdvancedGraphVisualizer:
    def __init__(self, master):
        self.master = master
        self.master.title("🍽️ Recipe Knowledge Graph Explorer")
        self.master.geometry("1600x950")
        self.master.configure(bg="#f0f0f0")
        
        # Load RDF graph
        self.rdf_graph = Graph()
        try:
            self.rdf_graph.parse(str(TTL_FILE), format="turtle")
        except Exception as e:
            messagebox.showerror("Error Loading Graph", 
                f"Could not load knowledge graph from {TTL_FILE}\n\nError: {str(e)}")
            self.master.destroy()
            return
        
        self.nx_graph = None
        self.pos = None
        self.selected_node = None
        self.highlighted_nodes = set()
        self.node_info = {}
        self.all_nodes_by_type = {'recipe': [], 'ingredient': [], 'nutrition': [], 'other': []}
        
        self.setup_ui()
        self.show_welcome_message()
        self.rebuild_graph_async()
        
    def setup_ui(self):
        # Modern style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        # Color scheme
        bg_color = "#f0f0f0"
        panel_bg = "#ffffff"
        accent_color = "#2196F3"
        text_color = "#212121"
        
        style.configure('Modern.TFrame', background=bg_color)
        style.configure('Panel.TFrame', background=panel_bg, relief='flat')
        style.configure('Modern.TLabel', background=panel_bg, foreground=text_color, font=('Segoe UI', 10))
        style.configure('Modern.TButton', font=('Segoe UI', 10), padding=8)
        style.configure('Accent.TButton', background=accent_color, foreground='white', font=('Segoe UI', 10, 'bold'))
        style.configure('Title.TLabel', background=panel_bg, foreground=accent_color, font=('Segoe UI', 24, 'bold'))
        style.configure('Section.TLabel', background=panel_bg, foreground=text_color, font=('Segoe UI', 12, 'bold'))
        
        # Main container with padding
        main_container = ttk.Frame(self.master, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header section
        header_frame = ttk.Frame(main_container, style='Panel.TFrame', relief='solid', borderwidth=1)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_container = ttk.Frame(header_frame, style='Panel.TFrame')
        title_container.pack(pady=20, padx=20)
        
        ttk.Label(title_container, text="🍽️ Recipe Knowledge Graph Explorer", 
                 style='Title.TLabel').pack()
        ttk.Label(title_container, text="Visualize and explore recipe relationships", 
                 style='Modern.TLabel', font=('Segoe UI', 11)).pack(pady=(5, 0))
        
        # Content area - three columns
        content_frame = ttk.Frame(main_container, style='Modern.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # LEFT PANEL - Controls
        left_panel = ttk.Frame(content_frame, style='Panel.TFrame', relief='solid', borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), ipadx=10, ipady=10)
        
        # Controls section header
        controls_header = ttk.Frame(left_panel, style='Panel.TFrame')
        controls_header.pack(fill=tk.X, pady=(10, 15), padx=10)
        ttk.Label(controls_header, text="⚙️ Graph Controls", style='Section.TLabel').pack(anchor=tk.W)
        
        # Recipe limit control with better feedback
        limit_frame = ttk.LabelFrame(left_panel, text="Number of Recipes to Display", padding=10)
        limit_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Number of recipes to include
        self.recipe_limit = tk.IntVar(value=5)
        
        # Get total number of recipes for max value
        total_recipes = len(list(self.rdf_graph.subjects(RDF.type, SCHEMA.Recipe)))
        
        self.recipe_limit_display = ttk.Label(limit_frame, text="5 recipes", 
                                              font=('Segoe UI', 14, 'bold'), foreground='#2196F3')
        self.recipe_limit_display.pack(pady=(0, 5))
        
        recipe_scale = ttk.Scale(limit_frame, from_=1, to=total_recipes, variable=self.recipe_limit, 
                                 orient=tk.HORIZONTAL, length=200)
        recipe_scale.pack(fill=tk.X, pady=5)
        
        hint_label = ttk.Label(limit_frame, text=f"Move slider (1-{total_recipes} recipes available)", 
                              font=('Segoe UI', 8), foreground='#666666')
        hint_label.pack()
        
        self.rebuild_timer = None
        
        def on_scale_change(v):
            value = int(float(v))
            self.recipe_limit_display.config(text=f"{value} recipe{'s' if value != 1 else ''}")
            if self.rebuild_timer:
                self.master.after_cancel(self.rebuild_timer)
            self.rebuild_timer = self.master.after(500, self.rebuild_graph_async)
        
        recipe_scale.configure(command=on_scale_change)
        
        # Layout selection
        layout_frame = ttk.LabelFrame(left_panel, text="Graph Layout Style", padding=10)
        layout_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.layout_var = tk.StringVar(value="spring")
        layouts = [
            ("🌸 Spring (Default)", "spring", "Natural, organic layout"),
            ("🌀 Spiral", "spiral", "Circular spiral pattern"),
            ("🎯 Force-Directed", "kamada_kawai", "Balanced distances")
        ]
        
        for text, value, desc in layouts:
            frame = ttk.Frame(layout_frame, style='Panel.TFrame')
            frame.pack(fill=tk.X, pady=2)
            rb = ttk.Radiobutton(frame, text=text, variable=self.layout_var, value=value)
            rb.pack(anchor=tk.W)
            ttk.Label(frame, text=desc, font=('Segoe UI', 8), 
                     foreground='#666666').pack(anchor=tk.W, padx=(20, 0))
        
        self.layout_var.trace('w', lambda *args: self.refresh_graph())
        
        # Action buttons
        button_frame = ttk.LabelFrame(left_panel, text="Actions", padding=10)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        buttons = [
            ("🔄 Refresh Graph", self.rebuild_graph_async, "Reload data from file"),
            ("📊 View Statistics", self.show_stats, "Show graph metrics"),
            ("💾 Export as Image", self.export_image, "Save graph as PNG"),
            ("ℹ️ Help", self.show_help, "How to use this tool")
        ]
        
        for text, command, tooltip in buttons:
            btn = ttk.Button(button_frame, text=text, command=command)
            btn.pack(pady=3, fill=tk.X)
            self.create_tooltip(btn, tooltip)
        
        # Search section
        search_frame = ttk.LabelFrame(left_panel, text="🔍 Search", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Segoe UI', 10))
        search_entry.pack(fill=tk.X, pady=(0, 5))
        search_entry.bind('<Return>', lambda e: self.search_graph())
        
        ttk.Button(search_frame, text="Search Recipes & Ingredients", 
                  command=self.search_graph).pack(fill=tk.X)
        
        # Legend
        legend_frame = ttk.LabelFrame(left_panel, text="🎨 Node Types", padding=10)
        legend_frame.pack(fill=tk.X, padx=10, pady=10)
        
        legends = [
            ("🍽️ Recipes", "#61dafb"),
            ("🥕 Ingredients", "#ffcc00"),
            ("📊 Nutrition Info", "#ff69b4"),
            ("📋 Other", "#cccccc")
        ]
        
        for text, color in legends:
            frame = ttk.Frame(legend_frame, style='Panel.TFrame')
            frame.pack(fill=tk.X, pady=2)
            canvas = tk.Canvas(frame, width=20, height=20, bg=panel_bg, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=(0, 10))
            canvas.create_oval(2, 2, 18, 18, fill=color, outline='#333333')
            ttk.Label(frame, text=text, style='Modern.TLabel').pack(side=tk.LEFT)
        
        # CENTER PANEL - Graph
        graph_panel = ttk.Frame(content_frame, style='Panel.TFrame', relief='solid', borderwidth=1)
        graph_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        graph_header = ttk.Frame(graph_panel, style='Panel.TFrame')
        graph_header.pack(fill=tk.X, pady=10, padx=10)
        ttk.Label(graph_header, text="📊 Graph Visualization", style='Section.TLabel').pack(anchor=tk.W)
        ttk.Label(graph_header, text="Click on nodes to view details", 
                 font=('Segoe UI', 9), foreground='#666666').pack(anchor=tk.W)
        
        self.fig = Figure(figsize=(10, 8), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#fafafa')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_panel)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        toolbar_frame = ttk.Frame(graph_panel, style='Panel.TFrame')
        toolbar_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        
        # RIGHT PANEL - Info
        right_panel = ttk.Frame(content_frame, style='Panel.TFrame', relief='solid', borderwidth=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        info_header = ttk.Frame(right_panel, style='Panel.TFrame')
        info_header.pack(fill=tk.X, pady=10, padx=10)
        ttk.Label(info_header, text="ℹ️ Node Details", style='Section.TLabel').pack(anchor=tk.W)
        
        # Scrolled text for info
        self.info_text = scrolledtext.ScrolledText(
            right_panel, 
            wrap=tk.WORD, 
            bg="#fafafa", 
            fg="#212121", 
            font=('Consolas', 10),
            relief='flat',
            padx=15,
            pady=15
        )
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Text tags for formatting
        self.info_text.tag_configure('title', foreground='#2196F3', font=('Segoe UI', 14, 'bold'))
        self.info_text.tag_configure('header', foreground='#1976D2', font=('Segoe UI', 11, 'bold'))
        self.info_text.tag_configure('property', foreground='#0288D1', font=('Consolas', 10, 'bold'))
        self.info_text.tag_configure('value', foreground='#424242', font=('Consolas', 9))
        
        # Status bar at bottom
        self.status_bar = ttk.Label(main_container, text="Ready", relief='sunken', 
                                   font=('Segoe UI', 9), background='#e0e0e0', foreground='#424242')
        self.status_bar.pack(fill=tk.X, pady=(10, 0))
        
    def create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget"""
        def on_enter(event):
            self.status_bar.config(text=text)
        def on_leave(event):
            self.status_bar.config(text="Ready")
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
        
    def show_welcome_message(self):
        """Display welcome message in info panel"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        welcome = """Welcome to Recipe Knowledge Graph Explorer! 🎉

This tool helps you visualize and explore recipe data.

🖱️ Getting Started:
• Click on any node to see detailed information
• Use the slider to adjust how many recipes to display
• Try different layout styles for better visualization
• Search for specific recipes or ingredients
• Hover over buttons to see helpful tips

📊 What You'll See:
• Blue nodes = Recipes
• Yellow nodes = Ingredients  
• Pink nodes = Nutrition information
• Gray nodes = Other data

💡 Pro Tips:
• Start with fewer recipes for clearer visualization
• Use the Spring layout for most cases
• Click "View Statistics" to see graph metrics
• Export your visualization as an image to share

Loading your graph now..."""

        self.info_text.insert(tk.END, welcome)
        self.info_text.config(state=tk.DISABLED)
        
    def show_help(self):
        """Show help dialog"""
        help_text = """📖 How to Use the Recipe Knowledge Graph Explorer

🔍 NAVIGATION:
• Click on nodes to view their properties
• Pan: Click and drag the background
• Zoom: Use mouse wheel or toolbar buttons
• Reset view: Click the home icon in toolbar

⚙️ CONTROLS:
• Recipe Slider: Adjust number of recipes shown
• Layout Options: Choose visualization style
• Search: Find specific recipes or ingredients
• Refresh: Reload graph from file

🎨 COLOR CODING:
• Blue circles = Recipe nodes (larger)
• Yellow circles = Ingredient nodes
• Pink circles = Nutrition information
• Gray circles = Other related data

💾 EXPORT:
Click "Export as Image" to save your current
visualization as a high-quality PNG file.

📊 STATISTICS:
View detailed metrics about the knowledge graph
including node counts and relationships.

Need more help? Check the documentation!"""
        
        messagebox.showinfo("Help - Recipe Graph Explorer", help_text)
        
    def _get_type(self, node_uri):
        node_type = self.rdf_graph.value(node_uri, RDF.type)
        if node_type == SCHEMA.Recipe:
            return 'recipe'
        elif node_type == FOOD.Ingredient:
            return 'ingredient'
        elif node_type == SCHEMA.NutritionInformation:
            return 'nutrition'
        else:
            return 'other'
        
    def _get_label(self, node_uri):
        """Get a human-readable label for a node"""
        # First try to get the recipe name
        label = self.rdf_graph.value(node_uri, SCHEMA.name)
        if label:
            return str(label)
        
        # Try RDFS label
        label = self.rdf_graph.value(node_uri, RDFS.label)
        if label:
            return str(label)
        
        # Extract from URI - get the last part after the last slash
        uri_str = str(node_uri)
        if '/' in uri_str:
            last_part = uri_str.split('/')[-1]
            # Replace underscores with spaces and capitalize
            return last_part.replace('_', ' ').title()
        
        return uri_str
    
    def _ensure_node_attributes(self, node_str):
        """Ensure a node has type and label attributes"""
        if node_str not in self.nx_graph.nodes:
            node_uri = URIRef(node_str)
            node_type = self._get_type(node_uri)
            label = self._get_label(node_uri)
            self.nx_graph.add_node(node_str, type=node_type, label=label)
            self.all_nodes_by_type[node_type].append(node_str)
        elif 'type' not in self.nx_graph.nodes[node_str]:
            node_uri = URIRef(node_str)
            node_type = self._get_type(node_uri)
            label = self._get_label(node_uri)
            self.nx_graph.nodes[node_str]['type'] = node_type
            self.nx_graph.nodes[node_str]['label'] = label
            self.all_nodes_by_type[node_type].append(node_str)
        
    def rebuild_graph_async(self):
        """Rebuild the graph with current settings"""
        self.status_bar.config(text="🔄 Building graph... Please wait...")
        self.master.update()
        
        try:
            limit = self.recipe_limit.get()
            
            # Get all recipes
            recipes = list(self.rdf_graph.subjects(RDF.type, SCHEMA.Recipe))
            
            if not recipes:
                messagebox.showwarning("No Data", "No recipes found in the knowledge graph!")
                self.status_bar.config(text="Ready - No recipes found")
                return
            
            # Sample up to limit recipes
            selected_recipes = random.sample(recipes, min(limit, len(recipes)))
            
            self.nx_graph = nx.MultiDiGraph()
            self.node_info = {}
            self.all_nodes_by_type = {'recipe': [], 'ingredient': [], 'nutrition': [], 'other': []}
            
            visited = set()
            
            def add_subgraph(current_node, depth=2):
                node_str = str(current_node)
                if node_str in visited or depth == 0:
                    return
                visited.add(node_str)
                
                node_uri = URIRef(node_str)
                node_type = self._get_type(node_uri)
                label = self._get_label(node_uri)
                
                self.nx_graph.add_node(node_str, type=node_type, label=label)
                self.all_nodes_by_type[node_type].append(node_str)
                
                properties = []
                for p, o in self.rdf_graph.predicate_objects(node_uri):
                    prop_label = str(p).split('/')[-1].split('#')[-1]
                    obj_str = str(o)
                    properties.append((prop_label, obj_str))
                    
                    if isinstance(o, URIRef):
                        o_str = str(o)
                        self._ensure_node_attributes(o_str)
                        self.nx_graph.add_edge(node_str, o_str, label=prop_label)
                        add_subgraph(o, depth-1)
                
                self.node_info[node_str] = {
                    'uri': node_str,
                    'type': node_type,
                    'label': label,
                    'properties': properties
                }
            
            for recipe in selected_recipes:
                add_subgraph(recipe)
            
            self.refresh_graph()
            self.status_bar.config(text=f"✅ Graph loaded: {len(self.nx_graph.nodes())} nodes, {len(self.nx_graph.edges())} connections")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to build graph:\n{str(e)}")
            self.status_bar.config(text="❌ Error building graph")
        
    def refresh_graph(self):
        """Redraw the graph visualization"""
        if not self.nx_graph or len(self.nx_graph.nodes()) == 0:
            return
        
        self.status_bar.config(text="🎨 Drawing graph...")
        self.master.update()
        
        self.ax.clear()
        
        layout = self.layout_var.get()
        try:
            if layout == "spring":
                self.pos = nx.spring_layout(self.nx_graph, k=0.8, iterations=50, seed=42)
            elif layout == "spiral":
                self.pos = nx.spiral_layout(self.nx_graph)
            elif layout == "kamada_kawai":
                self.pos = nx.kamada_kawai_layout(self.nx_graph)
        except:
            self.pos = nx.spring_layout(self.nx_graph, k=0.8, iterations=50, seed=42)
        
        # Color mapping
        color_map = {
            'recipe': '#61dafb',
            'ingredient': '#ffcc00',
            'nutrition': '#ff69b4',
            'other': '#cccccc'
        }
        
        # Get colors and sizes
        node_colors = []
        node_sizes = []
        edge_colors = []
        
        for n in self.nx_graph.nodes():
            node_type = self.nx_graph.nodes[n].get('type', 'other')
            
            # Highlight selected node
            if n == self.selected_node:
                node_colors.append('#FF5722')  # Bright red for selection
                node_sizes.append(1200)
            else:
                node_colors.append(color_map.get(node_type, '#cccccc'))
                node_sizes.append(900 if node_type == 'recipe' else 600)
        
        # Draw nodes with border
        nx.draw_networkx_nodes(
            self.nx_graph, self.pos, 
            node_color=node_colors, 
            node_size=node_sizes, 
            ax=self.ax,
            edgecolors='#333333',
            linewidths=2
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            self.nx_graph, self.pos, 
            arrowstyle='->', 
            arrowsize=15, 
            edge_color='#999999',
            width=1.5,
            ax=self.ax,
            connectionstyle='arc3,rad=0.1'
        )
        
        # Node labels
        labels = {}
        for n in self.nx_graph.nodes():
            node_label = self.nx_graph.nodes[n].get('label', str(n).split('/')[-1])
            # Truncate long labels
            if len(node_label) > 25:
                labels[n] = node_label[:22] + '...'
            else:
                labels[n] = node_label
        
        nx.draw_networkx_labels(
            self.nx_graph, self.pos, labels, 
            font_size=9, 
            font_weight='bold',
            font_color='#212121', 
            ax=self.ax
        )
        
        self.ax.set_facecolor('#fafafa')
        self.ax.axis('off')
        self.fig.tight_layout()
        self.canvas.draw()
        
        self.status_bar.config(text="Ready - Click on nodes to view details")
        
    def on_hover(self, event):
        """Show node name on hover"""
        if event.xdata is None or event.ydata is None or self.pos is None:
            return
        
        # Find closest node
        min_dist = float('inf')
        closest_node = None
        for node, (x, y) in self.pos.items():
            dist = np.sqrt((x - event.xdata)**2 + (y - event.ydata)**2)
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        
        threshold = 0.05
        if min_dist < threshold and closest_node in self.node_info:
            self.status_bar.config(text=f"👆 {self.node_info[closest_node]['label']}")
        else:
            self.status_bar.config(text="Ready - Click on nodes to view details")
        
    def on_click(self, event):
        """Handle node clicks"""
        if event.xdata is None or event.ydata is None or self.pos is None:
            return
        
        # Find closest node
        min_dist = float('inf')
        closest_node = None
        for node, (x, y) in self.pos.items():
            dist = np.sqrt((x - event.xdata)**2 + (y - event.ydata)**2)
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        
        threshold = 0.05
        if min_dist < threshold:
            self.selected_node = closest_node
            self.show_node_info(closest_node)
            self.refresh_graph()
        
    def show_node_info(self, node):
        """Display detailed information about a node"""
        if node not in self.node_info:
            return
        
        info = self.node_info[node]
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        # Title
        type_emoji = {
            'recipe': '🍽️',
            'ingredient': '🥕',
            'nutrition': '📊',
            'other': '📋'
        }
        
        emoji = type_emoji.get(info['type'], '📋')
        self.info_text.insert(tk.END, f"{emoji} {info['label']}\n", 'title')
        self.info_text.insert(tk.END, f"\n{'─' * 50}\n\n", 'value')
        
        # Type
        self.info_text.insert(tk.END, "Type: ", 'property')
        self.info_text.insert(tk.END, f"{info['type'].upper()}\n\n", 'value')
        
        # Properties
        self.info_text.insert(tk.END, "Properties:\n\n", 'header')
        
        # Group properties by importance
        important_props = ['name', 'recipeIngredient', 'recipeInstructions', 'description', 
                          'calories', 'proteinContent', 'fatContent', 'carbohydrateContent']
        
        displayed = set()
        
        # Show important properties first
        for prop, obj in info['properties']:
            if any(imp in prop for imp in important_props) and prop not in displayed:
                self.info_text.insert(tk.END, f"  • {prop}\n", 'property')
                # Truncate long values
                if len(obj) > 200:
                    obj = obj[:200] + "..."
                self.info_text.insert(tk.END, f"    {obj}\n\n", 'value')
                displayed.add(prop)
        
        # Show remaining properties
        remaining = [(p, o) for p, o in info['properties'] if p not in displayed]
        if remaining:
            self.info_text.insert(tk.END, "\nOther Properties:\n\n", 'header')
            for prop, obj in remaining[:20]:  # Limit to prevent overload
                self.info_text.insert(tk.END, f"  • {prop}\n", 'property')
                if len(obj) > 150:
                    obj = obj[:150] + "..."
                self.info_text.insert(tk.END, f"    {obj}\n\n", 'value')
        
        # URI at the bottom
        self.info_text.insert(tk.END, f"\n{'─' * 50}\n", 'value')
        self.info_text.insert(tk.END, f"URI: {info['uri']}\n", 'value')
        
        self.info_text.config(state=tk.DISABLED)
        self.info_text.see('1.0')  # Scroll to top
        
    def search_graph(self):
        """Search for nodes by name"""
        query = self.search_var.get().strip().lower()
        if not query:
            messagebox.showwarning("Search", "Please enter a search term")
            return
        
        self.status_bar.config(text=f"🔍 Searching for '{query}'...")
        
        matches = [
            node for node in self.nx_graph.nodes() 
            if node in self.node_info and query in self.node_info[node]['label'].lower()
        ]
        
        if matches:
            self.selected_node = matches[0]
            self.show_node_info(matches[0])
            self.refresh_graph()
            
            if len(matches) > 1:
                result_text = f"Found {len(matches)} matches:\n\n"
                for i, match in enumerate(matches[:10], 1):
                    result_text += f"{i}. {self.node_info[match]['label']}\n"
                if len(matches) > 10:
                    result_text += f"\n... and {len(matches) - 10} more"
                messagebox.showinfo("Search Results", result_text)
            else:
                messagebox.showinfo("Search Results", f"Found: {self.node_info[matches[0]]['label']}")
            
            self.status_bar.config(text=f"✅ Found {len(matches)} match(es)")
        else:
            messagebox.showinfo("Search Results", f"No results found for '{query}'")
            self.status_bar.config(text="❌ No matches found")
    
    def export_image(self):
        """Export the current graph as an image"""
        try:
            filename = "knowledge_graph_export.png"
            self.fig.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            messagebox.showinfo("Export Successful", 
                f"✅ Graph exported successfully!\n\nSaved as: {filename}\n\nYou can find it in your current directory.")
            self.status_bar.config(text=f"✅ Exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export image:\n{str(e)}")
            self.status_bar.config(text="❌ Export failed")
    
    def show_stats(self):
        """Display graph statistics"""
        if not self.nx_graph:
            messagebox.showwarning("No Graph", "Please load a graph first!")
            return
        
        try:
            density = nx.density(self.nx_graph)
        except:
            density = 0
        
        stats = f"""📊 Knowledge Graph Statistics
{'═' * 50}

📁 DATA SOURCE:
   {TTL_FILE}

🔢 OVERALL METRICS:
   • Total RDF Triples: {len(self.rdf_graph):,}
   • Nodes in Current View: {len(self.nx_graph.nodes()):,}
   • Edges in Current View: {len(self.nx_graph.edges()):,}
   • Graph Density: {density:.4f}

🏷️ NODE TYPES:
   🍽️  Recipes: {len(self.all_nodes_by_type['recipe'])}
   🥕  Ingredients: {len(self.all_nodes_by_type['ingredient'])}
   📊  Nutrition Info: {len(self.all_nodes_by_type['nutrition'])}
   📋  Other: {len(self.all_nodes_by_type['other'])}

💡 TIP: Adjust the recipe slider to explore more or less data!
"""
        messagebox.showinfo("Knowledge Graph Statistics", stats)

def visualize_rdf_graph(limit_nodes=80):
    """Launch the graph visualizer application"""
    root = tk.Tk()
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'+{x}+{y}')
    
    app = AdvancedGraphVisualizer(root)
    root.mainloop()

if __name__ == "__main__":
    visualize_rdf_graph()