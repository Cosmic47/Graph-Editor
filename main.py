import pygame
import easygui
import sys
import tkinter
import os.path
from ctypes import windll

# To fix blurry easygui UI
windll.shcore.SetProcessDpiAwareness(1)

# I hate you, pygame
pygame.font.init()

# Pygame related config
SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 1600, 900
FPS = 60
LMB, RMB, SCROLL_BTN = 1, 3, 5

# Graph UI config
BACKGR_COLOR = 255, 255, 255
VERTEX_RADIUS = 7
SELECTED_SIZE_INCREASE = 1.5
EDGE_THICKNESS = 5
EDGE_SELECT_SCALE = 3
VERTEX_COLOR = 0, 0, 0
EDGE_COLOR = 120, 120, 120
FONT = pygame.font.SysFont("Consolas", 20)

# General UI config
HOVER_SPEED = 6
MAX_SCALE = 1.2
SENSITIVITY = 3

# File-related stuff
EXTENSION = ".gph"
WRONG_FORMAT_MSG = "Wrong format", f"This file does not match the required file format ({EXTENSION}).\nDo you want to continue?"
FAILED_IMPORT_MSG = "Uh oh!", "Failed to import graph."


class Button:
    def __init__(self, x, y, img_name, callback):
        self.pos = pygame.Vector2(x, y)  # Left top corner
        self.img = pygame.image.load(img_name)  # Button's image
        self.callback = callback  # Function to call on click
        
        self.base_rect = pygame.Rect(x, y, *self.img.get_size())  # Initial rectangle of the button
        self.rect = self.base_rect.copy()  # Actual rectangle (after scaling)
        self.inflated = False  # Are we hovering on it?
        self.timer = 0  # Animation timer for hovering

    def draw(self, surface):
        # Blit image with scaling taken into account
        img = pygame.transform.smoothscale(self.img, (self.rect.width, self.rect.height))
        surface.blit(img, self.rect.topleft)

    def process_event(self, event):
        # Returns True if clicked otherwise False
        # Process hovering and LMB click
        self.inflated = self.rect.collidepoint(event.pos)

        # Call the function if we were clicked
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == LMB and self.inflated:
            self.callback()
            return True
        return False

    def update(self, dt):
        # Inflate or deflate if hovering with the mouse on it
        if self.inflated:
            self.timer = min(1, self.timer + HOVER_SPEED * dt)
        else:
            self.timer = max(0, self.timer - HOVER_SPEED * dt)

        scale = 1 + (MAX_SCALE - 1) * (self.timer ** 0.3)
        self.rect = self.base_rect.scale_by(scale)
        self.rect.center = self.base_rect.center

class ButtonManager:  # Basically stores, processes and draws all buttons
    def __init__(self):
        self.buttons = []

    def add_button(self, button):
        self.buttons.append(button)

    def draw(self, surface):
        for button in self.buttons:
            button.draw(surface)

    def process_event(self, event):
        # Return True if any of the buttons were clicked, otherwise False
        clicked_any = False
        for button in self.buttons:
            clicked_any = clicked_any or button.process_event(event)
        return clicked_any

    def update(self, dt):
        for button in self.buttons:
            button.update(dt)

class Vertex:
    def __init__(self, label, pos):
        self.label = label
        self.pos = pos
        self.visual_pos = pos

    def draw(self, surface, selected=False):
        pos = self.visual_pos
        
        # Draw all vertices (selected one has a doubled radius)
        radius = VERTEX_RADIUS * SELECTED_SIZE_INCREASE if selected else VERTEX_RADIUS
        pygame.draw.circle(surface, VERTEX_COLOR, pos, radius)

        # Draw name of the vertex directly above it
        label_surface = FONT.render(self.label, True, VERTEX_COLOR)
        label_rect = label_surface.get_rect()
        offset = pygame.Vector2(0, label_rect.height + VERTEX_RADIUS / 2) + label_rect.center
        surface.blit(label_surface, pos - offset)

class Graph:
    def __init__(self):
        self.vertices = []
        self.edges = []

    def add_vertex(self, x, y):
        self.vertices.append(Vertex("", pygame.Vector2(x, y)))

    def add_edge(self, idx1, idx2):
        self.edges.append((idx1, idx2))

    def move_vertex_to(self, idx, x, y):
        self.vertices[idx].pos = pygame.Vector2(x, y)

    def delete_vertex(self, idx):
        del self.vertices[idx]

        # We have to move all the indices after this one to make sure they point to right vertices
        new_edges = []
        for edge in self.edges:
            first_idx, second_idx = edge
            if idx in edge:
                continue
            if first_idx > idx:
                first_idx -= 1
            if second_idx > idx:
                second_idx -= 1
            new_edges.append((first_idx, second_idx))
        self.edges = new_edges

    def delete_edge(self, idx):
        del self.edges[idx]

    def get_vertex_at(self, x, y):
        for idx, vertex in enumerate(self.vertices):
            if vertex.pos.distance_squared_to((x, y)) < VERTEX_RADIUS * VERTEX_RADIUS:
                return idx
        return -1

    def get_edge_at(self, x, y):
        point = pygame.Vector2(x, y)
        
        for idx, edge in enumerate(self.edges):
            a, b = self.vertices[edge[0]].pos, self.vertices[edge[1]].pos

            # Calculate the distance of point from the edge
            displ = point - a
            r = b - a
            t = displ.dot(r) / r.dot(r)
            if t < 0:
                dist = a.distance_to(point)
            elif t > 1:
                dist = b.distance_to(point)
            else:
                dist = (displ - r * t).length()

            # We're going to go with an increased edge thickness for selection to make it easier to select
            if dist < EDGE_SELECT_SCALE * (EDGE_THICKNESS / 2):
                return idx

        return -1            

    def draw(self, surface, selected=-1):
        for edge in self.edges:
            start_pos = self.vertices[edge[0]].visual_pos
            end_pos = self.vertices[edge[1]].visual_pos
            pygame.draw.line(surface, EDGE_COLOR, start_pos, end_pos, EDGE_THICKNESS)
        
        for idx, vertex in enumerate(self.vertices):
            self.vertices[idx].draw(surface, selected == idx)

    def save(self, path):
        # Number of vertices, vertex data, number of edges, edge data
        with open(path, 'w') as file:
            file.write(f"{len(self.vertices)}\n")
            file.writelines([f"{vert.pos.x} {vert.pos.y} {vert.label}\n" for vert in self.vertices])
            file.write(f"{len(self.edges)}\n")
            file.writelines([f"{edge[0]} {edge[1]}\n" for edge in self.edges])

    @classmethod
    def load(cls, path):
        # See save
        graph = cls()
        
        with open(path, 'r') as file:
            vert_num = int(file.readline())
            for _ in range(vert_num):
                vert_data = file.readline().split()
                x, y, label = float(vert_data[0]), float(vert_data[1]), vert_data[2]
                graph.add_vertex(x, y)
                graph.vertices[-1].label = label
            edge_num = int(file.readline())
            for _ in range(edge_num):
                edge = tuple(map(int, file.readline().split()))
                graph.add_edge(*edge)

        return graph

    def shift(self, displacement):  # purely visual displacement
        for vert in self.vertices:
            vert.visual_pos += displacement

    def scale(self, scale, center):
        for vert in self.vertices:
            vert.visual_pos = (vert.visual_pos - center) * scale + center

class App:
    VERTEX_MODE, EDGE_MODE, TEXT_MODE, NAVIGATION_MODE = range(4)  # App states

    def __init__(self):
        self.state = App.VERTEX_MODE

        self.selected = -1  # Index of a vertex we're grabbing
        
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.dt = 1 / FPS

        self.buttons = ButtonManager()
        self.init_buttons()

        self.graph = Graph()
        self.zoom = 1
        self.offset = pygame.Vector2(0, 0)

    def init_buttons(self):
        # TODO: make dynamic repositioning
        self.buttons.add_button(Button(30, 815, "icons\\vertex mode button.png", lambda: self.change_state(App.VERTEX_MODE)))
        self.buttons.add_button(Button(110, 815, "icons\\edge mode button.png", lambda: self.change_state(App.EDGE_MODE)))
        self.buttons.add_button(Button(190, 815, "icons\\text mode button.png", lambda: self.change_state(App.TEXT_MODE)))
        self.buttons.add_button(Button(270, 815, "icons\\navigation mode button.png", lambda: self.change_state(App.NAVIGATION_MODE)))

        self.buttons.add_button(Button(30, 20, "icons\\save button.png", lambda: self.save_file()))
        self.buttons.add_button(Button(110, 20, "icons\\load button.png", lambda: self.load_file()))

        self.buttons.add_button(Button(1515, 815, "icons\\screenshot button.png", lambda: self.screenshot()))

    def scale_zoom(self, intensity):
        zoom_center = pygame.mouse.get_pos()
        diff = self.dt * intensity * SENSITIVITY

        if self.zoom + diff > 0.1:
            self.graph.scale((self.zoom + diff) / self.zoom, zoom_center)
            self.zoom += diff

    def screenshot(self):
        surface = pygame.Surface(SCREEN_SIZE)
        surface.fill(BACKGR_COLOR)
        self.graph.draw(surface, selected=self.selected)
        filename = "screenshot.png"
        i = 1
        while os.path.exists(filename):
            filename = f"screenshot ({i}).png"
            i += 1
        pygame.image.save(surface, filename)

    def save_file(self):
        filename = easygui.filesavebox(default="New Graph", filetypes=[[f"*{EXTENSION}", "Graph files"]])

        # If chose nothing, do nothing
        if not filename:
            return

        # Unless it is specified already, don't add extension
        if not filename.endswith(EXTENSION):
            filename += EXTENSION

        self.graph.save(filename)

    def load_file(self):
        filepath = easygui.fileopenbox()
        if not filepath:
            return

        # Ask user if doesn't match format
        all_good = True
        if not filepath.endswith(EXTENSION):
            all_good = tkinter.messagebox.askyesno(*WRONG_FORMAT_MSG)

        if all_good:
            try:
                self.graph = Graph.load(filepath)
            except UnicodeDecodeError:
                tkinter.messagebox.showerror(*FAILED_IMPORT_MSG)

    def process_mouse_in_vertex_mode(self, event):
        # Move a vertex we grabbed
        if self.selected != -1 and event.type == pygame.MOUSEMOTION:
            self.graph.move_vertex_to(self.selected, *event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Process click
            clicked_idx = self.graph.get_vertex_at(*event.pos)
            if event.button == LMB:
                # Left click is either create new vertex or select it for grabbing
                if clicked_idx == -1:
                    self.graph.add_vertex(*event.pos)
                else:
                    self.selected = clicked_idx
            
            elif event.button == RMB and clicked_idx != -1:
                # Right click on a vertex deletes it
                self.graph.delete_vertex(clicked_idx)
        
        elif event.type == pygame.MOUSEBUTTONUP:
            # Deselect vertex when we're done dragging it
            self.selected = -1

    def process_mouse_in_edge_mode(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            # We dont care about not clicking
            return

        if event.button == LMB:
            # Left click is related to edge creation
            clicked_idx = self.graph.get_vertex_at(*event.pos)

            if clicked_idx == -1:
                # Deselect if we didn't click on a vertex
                self.selected = -1
            else:
                if self.selected != -1:
                    self.graph.add_edge(self.selected, clicked_idx)
                    self.selected = -1
                else:
                    self.selected = clicked_idx
        elif event.button == RMB:
            # Right click is deletion of an edge
            clicked_idx = self.graph.get_edge_at(*event.pos)

            if clicked_idx != -1:
                self.graph.delete_edge(clicked_idx)

    def process_mouse_in_text_mode(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == LMB:
            clicked_idx = self.graph.get_vertex_at(*event.pos)
            if clicked_idx != -1:
                self.selected = clicked_idx

    def process_mouse_in_navigation_mode(self, event):
        if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            rel_x, rel_y = event.rel
            self.graph.shift(pygame.Vector2(rel_x, rel_y))
        if event.type == pygame.MOUSEWHEEL:
            self.scale_zoom(event.y)

    def process_keys_in_text_mode(self, event):
        # Do nothing if not selected
        if self.selected == -1:
            return

        label = self.graph.vertices[self.selected].label

        # Edit label
        if event.key == pygame.K_BACKSPACE:
            label = label[:-1]
        elif event.key == pygame.K_RETURN:
            self.selected = -1
            return
        elif event.unicode:
            label += event.unicode

        self.graph.vertices[self.selected].label = label

    def handle_graph_mouse_interactions(self, event):
        if self.state == App.VERTEX_MODE:
            self.process_mouse_in_vertex_mode(event)
        elif self.state == App.EDGE_MODE:
            self.process_mouse_in_edge_mode(event)
        elif self.state == App.TEXT_MODE:
            self.process_mouse_in_text_mode(event)
        elif self.state == App.NAVIGATION_MODE:
            self.process_mouse_in_navigation_mode(event)

    def change_state(self, new_state):
        self.selected = -1  # Deselect whenever state is changed
        self.state = new_state

    def draw(self):
        # Clear the screen
        self.screen.fill(BACKGR_COLOR)

        # When in edge mode having already selected vertex, draw an edge from it to your cursor.
        # As if you're stretching it from one vertex to another
        if self.state == App.EDGE_MODE and self.selected != -1:
            mouse_pos = pygame.mouse.get_pos()
            pygame.draw.line(self.screen, EDGE_COLOR, self.graph.vertices[self.selected].pos, mouse_pos, EDGE_THICKNESS)

        # Draw the graph with specified selected vertex
        self.graph.draw(self.screen, selected=self.selected)

        # Draw buttons
        self.buttons.draw(self.screen)

        pygame.display.update()

    def run(self):
        self.dt = 1 / FPS
        clock = pygame.time.Clock()
        
        while True:
            for event in pygame.event.get():
                # Quitting
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Typing
                if event.type == pygame.KEYDOWN and self.state == App.TEXT_MODE:
                    self.process_keys_in_text_mode(event)

                # Processing mouse events by UI elements and, if no click happened, by graph elements
                clicked_any = False
                if event.type in [pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION]:
                    clicked_any = self.buttons.process_event(event)
                if not clicked_any or event.type == pygame.MOUSEWHEEL:
                    self.handle_graph_mouse_interactions(event)                

            self.buttons.update(self.dt)
            
            self.draw()
            
            self.dt = clock.tick(FPS) / 1000   

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Graph Editor v1.0.69")

    app = App()
    app.run()
